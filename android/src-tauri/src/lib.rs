//! Android shell. OSA stays on the server. This window is the server's web UI.
//! No push and no in-app sheet in this version. Reports open in the same window.

mod connect;
mod store;

use serde_json::{json, Value};
use std::path::PathBuf;
use std::sync::Mutex;
use tauri::ipc::CapabilityBuilder;
use tauri::{AppHandle, Manager, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_opener::OpenerExt;
use url::Url;

use connect::Pair;

const BRIDGE: &str = r#"(function () {
  if (window.osaDesktop || window.top !== window || !/^https?:$/.test(location.protocol) || location.origin === 'null') return;
  var call = function (cmd, args) { return window.__TAURI_INTERNALS__.invoke(cmd, args || {}); };
  var quiet = function (cmd, args) { try { call(cmd, args).catch(function () {}); } catch (e) {} };
  window.osaDesktop = {
    platform: 'android',
    notify: function () {},
    setBadge: function (count) { quiet('android_set_badge', { count: count | 0 }); },
    openExternal: function (url) { quiet('android_open_external', { url: String(url) }); },
    speech: false,
    openSheet: function (url) { return call('android_open_sheet', { url: String(url) }); },
    switchServer: function () {
      call('android_switch_server').then(function () {
        location.replace('http://tauri.localhost/');
      }).catch(function () {});
    }
  };
})();"#;

const UI_PATHS: &str = r"/:p(|apps/?|library/?|library/pages/\d+/?)";

pub struct State {
    dir: PathBuf,
    cfg: Mutex<store::Config>,
    origin: Mutex<Option<Url>>,
    granted: Mutex<Vec<String>>,
    pair: Mutex<Option<Pair>>,
    error: Mutex<String>,
    next: Mutex<Option<String>>,
    checking: Mutex<bool>,
    probe: Mutex<connect::ProbeGate>,
}

fn state(app: &AppHandle) -> tauri::State<'_, State> {
    app.state::<State>()
}

fn show_setup(app: &AppHandle, query: &str) {
    let st = state(app);
    *st.origin.lock().unwrap() = None;
    st.next.lock().unwrap().take();
    *st.checking.lock().unwrap() = false;
    let _ = query;
    // The setup page reads setup_state and moves itself with location.replace.
    // wry 0.57.2 android/main_pipe.rs uses a bounded(8) channel and blocking send.
    // WebviewWindow::navigate posts onto that channel. The UI thread drains it,
    // so a full channel on that thread never returns and Android kills the process.
}

fn server_pattern(origin: &Url) -> String {
    format!("{}{UI_PATHS}", origin.origin().ascii_serialization())
}

fn bump_probe(app: &AppHandle) -> u64 {
    let st = state(app);
    let gen = st.probe.lock().unwrap().bump();
    *st.checking.lock().unwrap() = false;
    gen
}

/// Apply only while `gen` is still the latest probe. Holds the gate for the whole apply.
fn apply_current(app: &AppHandle, gen: u64, apply: impl FnOnce()) -> bool {
    let st = state(app);
    let gate = st.probe.lock().unwrap();
    if !gate.is_current(gen) {
        return false;
    }
    apply();
    true
}

fn begin_probe(app: &AppHandle, origin: Url, ticket: String) {
    let gen = bump_probe(app);
    {
        let st = state(app);
        let gate = st.probe.lock().unwrap();
        if gate.is_current(gen) {
            *st.checking.lock().unwrap() = true;
        }
    }
    let app = app.clone();
    std::thread::spawn(move || {
        let result = connect::probe(&origin);
        if !apply_current(&app, gen, || match result {
            Ok(()) => finish_connect(&app, origin, &ticket),
            Err(e) => {
                *state(&app).error.lock().unwrap() = e;
                show_setup(&app, "");
            }
        }) {
            return;
        }
    });
}

fn finish_connect(app: &AppHandle, origin: Url, ticket: &str) {
    {
        let st = state(app);
        let mut cfg = st.cfg.lock().unwrap();
        cfg.url = Some(origin.origin().ascii_serialization());
        store::save(&st.dir, &cfg);
    }
    let first = (!ticket.is_empty()).then(|| connect::ticket_url(&origin, ticket));
    open_server(app, origin, first);
    *state(app).checking.lock().unwrap() = false;
}

fn grant(app: &AppHandle, origin: &Url) {
    let key = origin.origin().ascii_serialization();
    let st = state(app);
    let mut granted = st.granted.lock().unwrap();
    if granted.contains(&key) {
        return;
    }
    let cap = CapabilityBuilder::new(format!("server-{}", granted.len()))
        .remote(server_pattern(origin))
        .local(false)
        .window("main")
        .permission("core:default")
        .permission("allow-android-open-external")
        .permission("allow-android-switch-server")
        .permission("allow-android-open-sheet")
        .permission("allow-android-set-badge");
    if app.add_capability(cap).is_ok() {
        granted.push(key);
    }
}

fn open_server(app: &AppHandle, origin: Url, first: Option<Url>) {
    *state(app).origin.lock().unwrap() = Some(origin.clone());
    state(app).error.lock().unwrap().clear();
    *state(app).next.lock().unwrap() = Some(first.unwrap_or(origin.clone()).to_string());
    grant(app, &origin);
}

#[cfg_attr(not(any(target_os = "macos", target_os = "ios", target_os = "android")), allow(dead_code))]
fn on_pair(app: &AppHandle, pair: Pair) {
    let configured = state(app).cfg.lock().unwrap().url.clone().and_then(|u| connect::normalize(&u));
    if configured.as_ref().is_some_and(|c| c.origin() != pair.server.origin()) {
        bump_probe(app);
        *state(app).pair.lock().unwrap() = Some(pair);
        *state(app).next.lock().unwrap() = None;
        return;
    }
    begin_probe(app, pair.server, pair.ticket);
}

#[tauri::command]
fn setup_state(app: AppHandle) -> Value {
    let st = state(&app);
    let url = st.cfg.lock().unwrap().url.clone();
    let pair = st.pair.lock().unwrap().clone();
    json!({
        "url": url,
        "error": st.error.lock().unwrap().clone(),
        "pair": pair.map(|p| p.server.origin().ascii_serialization()),
        "next": st.next.lock().unwrap().clone(),
        "checking": *st.checking.lock().unwrap(),
    })
}

#[tauri::command(async)]
fn choose_remote(app: AppHandle, url: String) -> Result<(), String> {
    let origin = connect::normalize(&url).ok_or_else(|| "Địa chỉ chưa đúng. Ví dụ http://192.168.1.10:8765".to_string())?;
    let gen = bump_probe(&app);
    let result = connect::probe(&origin);
    let mut outcome = Ok(());
    if !apply_current(&app, gen, || match result {
        Ok(()) => finish_connect(&app, origin, ""),
        Err(e) => outcome = Err(e),
    }) {
        return Ok(());
    }
    outcome
}

#[tauri::command(async)]
fn confirm_pair(app: AppHandle) -> Result<(), String> {
    let pair = state(&app).pair.lock().unwrap().take().ok_or("no pending pair")?;
    let gen = bump_probe(&app);
    let result = connect::probe(&pair.server);
    let mut outcome = Ok(());
    if !apply_current(&app, gen, || match &result {
        Ok(()) => finish_connect(&app, pair.server, &pair.ticket),
        Err(e) => outcome = Err(e.clone()),
    }) {
        return Ok(());
    }
    outcome
}

#[tauri::command]
fn cancel_pair(app: AppHandle) {
    bump_probe(&app);
    state(&app).pair.lock().unwrap().take();
    let configured = state(&app).cfg.lock().unwrap().url.clone().and_then(|u| connect::normalize(&u));
    if let Some(origin) = configured {
        open_server(&app, origin, None);
    }
}

#[tauri::command]
fn android_open_external(app: AppHandle, url: String) {
    if let Ok(u) = Url::parse(&url) {
        if matches!(u.scheme(), "http" | "https" | "mailto" | "tel") {
            let _ = app.opener().open_url(u.as_str(), None::<&str>);
        }
    }
}

#[tauri::command]
fn android_switch_server(app: AppHandle) {
    bump_probe(&app);
    {
        let st = state(&app);
        let mut cfg = st.cfg.lock().unwrap();
        cfg.url = None;
        store::save(&st.dir, &cfg);
        st.next.lock().unwrap().take();
        *st.origin.lock().unwrap() = None;
    }
    // The page reloads itself. navigate() fills wry's 8-message Android queue.
}

/// Same-origin pages open in a second Android activity. A second wry window
/// would share the 8-message queue that crashes the process.
#[tauri::command(async)]
async fn android_open_sheet(app: AppHandle, url: String) -> Result<(), String> {
    let origin = state(&app).origin.lock().unwrap().clone().ok_or("no server")?;
    let u = origin.join(&url).map_err(|e| e.to_string())?;
    if u.origin() != origin.origin() {
        let _ = app.opener().open_url(u.as_str(), None::<&str>);
        return Ok(());
    }
    let origin = origin.origin().ascii_serialization();
    tauri::async_runtime::spawn_blocking(move || start_sheet(&u, &origin))
        .await
        .map_err(|e| e.to_string())?
}

#[cfg(target_os = "android")]
fn start_sheet(url: &Url, origin: &str) -> Result<(), String> {
    use jni::objects::{JObject, JValue};
    let ctx = ndk_context::android_context();
    let vm = unsafe { jni::JavaVM::from_raw(ctx.vm().cast()) }.map_err(|e| e.to_string())?;
    let mut env = vm.attach_current_thread().map_err(|e| e.to_string())?;
    let activity = unsafe { JObject::from_raw(ctx.context().cast()) };
    let class = env.find_class("com/kadaliao/opensuperagent/SheetActivity").map_err(|e| e.to_string())?;
    let url_s = env.new_string(url.as_str()).map_err(|e| e.to_string())?;
    let origin_s = env.new_string(origin).map_err(|e| e.to_string())?;
    env.call_static_method(
        class,
        "openAndWait",
        "(Landroid/app/Activity;Ljava/lang/String;Ljava/lang/String;)V",
        &[JValue::Object(&activity), JValue::Object(&url_s), JValue::Object(&origin_s)],
    ).map_err(|e| e.to_string())?;
    Ok(())
}

#[cfg(not(target_os = "android"))]
fn start_sheet(_url: &Url, _origin: &str) -> Result<(), String> {
    Err("android only".into())
}

#[tauri::command]
fn android_set_badge(count: i64) {
    set_badge(count.max(0));
}

#[cfg(target_os = "android")]
fn set_badge(count: i64) {
    use jni::objects::{JObject, JValue};
    let ctx = ndk_context::android_context();
    let Ok(vm) = (unsafe { jni::JavaVM::from_raw(ctx.vm().cast()) }) else { return };
    let Ok(mut env) = vm.attach_current_thread() else { return };
    let activity = unsafe { JObject::from_raw(ctx.context().cast()) };
    let Ok(class) = env.find_class("com/kadaliao/opensuperagent/SheetActivity") else { return };
    let _ = env.call_static_method(
        class,
        "setCount",
        "(Landroid/app/Activity;I)V",
        &[JValue::Object(&activity), JValue::Int(count as i32)],
    );
}

#[cfg(not(target_os = "android"))]
fn set_badge(_count: i64) {}

fn build_main(app: &AppHandle) -> tauri::Result<()> {
    WebviewWindowBuilder::new(app, "main", WebviewUrl::App("index.html".into()))
        .initialization_script(BRIDGE)
        .build()?;
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            setup_state, choose_remote, confirm_pair, cancel_pair,
            android_open_external, android_switch_server, android_open_sheet,
            android_set_badge
        ])
        .setup(|app| {
            let dir = app.path().app_data_dir().unwrap_or_else(|_| std::env::temp_dir());
            let cfg = store::load(&dir);
            let saved = cfg.url.clone();
            app.manage(State {
                dir,
                cfg: Mutex::new(cfg),
                origin: Mutex::new(None),
                granted: Mutex::new(vec![]),
                pair: Mutex::new(None),
                error: Mutex::new(String::new()),
                next: Mutex::new(None),
                checking: Mutex::new(false),
                probe: Mutex::new(connect::ProbeGate::default()),
            });
            let handle = app.handle().clone();
            build_main(&handle)?;
            // Desktop demo: OSA_ANDROID_URL=http://127.0.0.1:port cargo run
            // The Android binary ignores this so a device cannot be pointed at a hidden host.
            let demo = if cfg!(target_os = "android") {
                None
            } else {
                std::env::var("OSA_ANDROID_URL").ok()
            };
            let remembered = demo.as_deref().or(saved.as_deref()).and_then(connect::normalize);
            if let Some(origin) = remembered {
                begin_probe(&handle, origin, String::new());
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("Open Super Agent Android failed to start")
        .run(|app, event| {
            // Opened exists only on macOS and mobile. A Linux demo build has no such variant.
            #[cfg(any(target_os = "macos", target_os = "ios", target_os = "android"))]
            if let tauri::RunEvent::Opened { urls } = &event {
                for u in urls {
                    if let Ok(parsed) = Url::parse(u.as_str()) {
                        if let Some(pair) = connect::parse_pair(&parsed) {
                            on_pair(app, pair);
                        }
                    }
                }
            }
            let _ = (app, event);
        });
}
