//! Android shell. OSA stays on the server. This window is the server's web UI.
//! No push and no in-app sheet in this version. Reports open in the same window.

mod connect;
mod store;

use serde_json::{json, Value};
use std::path::PathBuf;
use std::sync::Mutex;
use std::time::Duration;
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
    setBadge: function () {},
    openExternal: function (url) { quiet('android_open_external', { url: String(url) }); },
    speech: false,
    switchServer: function () { quiet('android_switch_server'); }
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
}

fn state(app: &AppHandle) -> tauri::State<'_, State> {
    app.state::<State>()
}

fn show_setup(app: &AppHandle, query: &str) {
    *state(app).origin.lock().unwrap() = None;
    let _ = query;
    // The setup page reads setup_state and moves itself. navigate() goes
    // through wry's Android queue, which holds 8 messages and then panics.
}

fn server_pattern(origin: &Url) -> String {
    format!("{}{UI_PATHS}", origin.origin().ascii_serialization())
}

fn check_remote(origin: &Url) -> Result<(), String> {
    let agent = ureq::AgentBuilder::new().timeout(Duration::from_secs(15)).build();
    match agent.get(origin.join("/manifest.json").unwrap().as_str()).call() {
        Ok(_) => Ok(()),
        Err(e) => Err(format!("Can't reach this address: {e}")),
    }
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
        .permission("allow-android-open-external")
        .permission("allow-android-switch-server");
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

fn connect(app: &AppHandle, origin: Url, ticket: &str) -> Result<(), String> {
    check_remote(&origin)?;
    {
        let st = state(app);
        let mut cfg = st.cfg.lock().unwrap();
        cfg.url = Some(origin.origin().ascii_serialization());
        store::save(&st.dir, &cfg);
    }
    let first = (!ticket.is_empty()).then(|| connect::ticket_url(&origin, ticket));
    open_server(app, origin, first);
    Ok(())
}

fn on_pair(app: &AppHandle, pair: Pair) {
    let configured = state(app).cfg.lock().unwrap().url.clone().and_then(|u| connect::normalize(&u));
    if configured.as_ref().is_some_and(|c| c.origin() != pair.server.origin()) {
        *state(app).pair.lock().unwrap() = Some(pair);
        *state(app).next.lock().unwrap() = None;
        return;
    }
    let app = app.clone();
    std::thread::spawn(move || {
        if let Err(e) = connect(&app, pair.server, &pair.ticket) {
            *state(&app).error.lock().unwrap() = e;
            show_setup(&app, "");
        }
    });
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
    })
}

#[tauri::command(async)]
fn choose_remote(app: AppHandle, url: String) -> Result<(), String> {
    let origin = connect::normalize(&url).ok_or_else(|| "That address doesn't look right, e.g. https://osa.example.com".to_string())?;
    connect(&app, origin, "")
}

#[tauri::command(async)]
fn confirm_pair(app: AppHandle) -> Result<(), String> {
    let pair = state(&app).pair.lock().unwrap().take().ok_or("no pending pair")?;
    connect(&app, pair.server, &pair.ticket)
}

#[tauri::command]
fn cancel_pair(app: AppHandle) {
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
    show_setup(&app, "?switch=1");
}

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
            android_open_external, android_switch_server
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
            });
            let handle = app.handle().clone();
            build_main(&handle)?;
            if let Some(origin) = saved.as_deref().and_then(connect::normalize) {
                open_server(&handle, origin, None);
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("Open Super Agent Android failed to start")
        .run(|app, event| {
            if let tauri::RunEvent::Opened { urls } = event {
                for u in urls {
                    if let Ok(parsed) = Url::parse(u.as_str()) {
                        if let Some(pair) = connect::parse_pair(&parsed) {
                            on_pair(app, pair);
                        }
                    }
                }
            }
        });
}
