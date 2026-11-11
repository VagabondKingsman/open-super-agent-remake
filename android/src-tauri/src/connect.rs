//! Address and pairing rules for the Android shell.
//! The shell does not run OSA. It opens the server's own web UI.

use std::time::Duration;
use url::Url;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Pair {
    pub server: Url,
    pub ticket: String,
}

/// Keep scheme, host and port. A bare host is treated as https.
pub fn normalize(input: &str) -> Option<Url> {
    let s = input.trim();
    if s.is_empty() {
        return None;
    }
    let s = if s.contains("://") { s.to_string() } else { format!("https://{s}") };
    let u = Url::parse(&s).ok()?;
    if !matches!(u.scheme(), "http" | "https") || u.host_str().is_none() {
        return None;
    }
    Url::parse(&format!("{}/", u.origin().ascii_serialization())).ok()
}

/// `opensuperagent://pair?u=<server>&t=<one-time ticket>` from the QR.
#[cfg_attr(not(any(target_os = "macos", target_os = "ios", target_os = "android")), allow(dead_code))]
pub fn parse_pair(u: &Url) -> Option<Pair> {
    if u.scheme() != "opensuperagent" || u.host_str() != Some("pair") {
        return None;
    }
    let get = |k: &str| u.query_pairs().find(|(n, _)| n == k).map(|(_, v)| v.into_owned());
    let server = normalize(&get("u")?)?;
    let ticket = get("t").unwrap_or_default();
    if !ticket.is_empty() && !ticket.bytes().all(|b| b.is_ascii_alphanumeric() || b == b'-' || b == b'_') {
        return None;
    }
    Some(Pair { server, ticket })
}

pub fn ticket_url(origin: &Url, ticket: &str) -> Url {
    let mut u = origin.join("/login/ticket").expect("origin");
    u.query_pairs_mut().append_pair("t", ticket).append_pair("next", "/");
    u
}

/// One generation per connect attempt. A slower probe must not apply after a newer one.
#[derive(Clone, Copy, Debug, Default)]
pub struct ProbeGate {
    gen: u64,
}

impl ProbeGate {
    pub fn bump(&mut self) -> u64 {
        self.gen = self.gen.wrapping_add(1);
        self.gen
    }

    pub fn is_current(&self, gen: u64) -> bool {
        self.gen == gen
    }
}

/// GET `/manifest.json`. A transport or TLS failure is an error string.
/// A panic inside the HTTP stack becomes that same error, so the process stays up.
pub fn probe(origin: &Url) -> Result<(), String> {
    let url = origin.join("/manifest.json").map_err(|e| e.to_string())?;
    let probed = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        let agent = ureq::AgentBuilder::new().timeout(Duration::from_secs(15)).build();
        agent.get(url.as_str()).call().map(|_| ()).map_err(|e| e.to_string())
    }));
    match probed {
        Ok(Ok(())) => Ok(()),
        Ok(Err(e)) => Err(format!("Không tới được địa chỉ này: {e}")),
        Err(_) => Err("Không tới được địa chỉ này.".into()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bare_host_becomes_https_origin() {
        let u = normalize("osa.example.com/apps").unwrap();
        assert_eq!(u.as_str(), "https://osa.example.com/");
    }

    #[test]
    fn rejects_non_http() {
        assert!(normalize("javascript:alert(1)").is_none());
        assert!(normalize("file:///tmp").is_none());
    }

    #[test]
    fn pair_keeps_server_and_ticket() {
        let u = Url::parse("opensuperagent://pair?u=https://osa.example.com&t=abc-DEF_1").unwrap();
        let p = parse_pair(&u).unwrap();
        assert_eq!(p.server.as_str(), "https://osa.example.com/");
        assert_eq!(p.ticket, "abc-DEF_1");
        assert_eq!(ticket_url(&p.server, &p.ticket).as_str(), "https://osa.example.com/login/ticket?t=abc-DEF_1&next=%2F");
    }

    #[test]
    fn explicit_http_stays_http() {
        let u = normalize("http://192.168.1.10:8765").unwrap();
        assert_eq!(u.as_str(), "http://192.168.1.10:8765/");
    }

    #[test]
    fn bad_ticket_is_dropped() {
        let u = Url::parse("opensuperagent://pair?u=https://osa.example.com&t=a.b").unwrap();
        assert!(parse_pair(&u).is_none());
    }

    #[test]
    fn probe_refused_is_an_error_not_a_panic() {
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        drop(listener);
        let origin = Url::parse(&format!("http://127.0.0.1:{port}/")).unwrap();
        let err = probe(&origin).unwrap_err();
        assert!(err.starts_with("Không tới được địa chỉ này"));
    }

    #[test]
    fn probe_accepts_manifest() {
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        std::thread::spawn(move || {
            let Ok((mut sock, _)) = listener.accept() else { return };
            let mut buf = [0u8; 2048];
            let _ = std::io::Read::read(&mut sock, &mut buf);
            let body = br#"{"name":"osa"}"#;
            let head = format!(
                "HTTP/1.1 200 OK\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
                body.len()
            );
            let _ = std::io::Write::write_all(&mut sock, head.as_bytes());
            let _ = std::io::Write::write_all(&mut sock, body);
        });
        let origin = Url::parse(&format!("http://127.0.0.1:{port}/")).unwrap();
        probe(&origin).unwrap();
    }

    /// wry 0.57.2 `android/main_pipe.rs` uses `bounded(8)` and `send()` blocks.
    /// The UI thread is the only drainer. A 9th send from that thread never returns,
    /// Android kills the process. `lib.rs` must not call `WebviewWindow::navigate`.
    #[test]
    fn ninth_pipe_send_blocks_until_drained() {
        let (tx, rx) = std::sync::mpsc::sync_channel(8);
        for i in 0..8u8 {
            tx.send(i).unwrap();
        }
        let tx2 = tx.clone();
        let worker = std::thread::spawn(move || tx2.send(9u8));
        std::thread::sleep(Duration::from_millis(200));
        assert!(!worker.is_finished(), "the 9th send must still be blocked");
        for _ in 0..8 {
            rx.recv().unwrap();
        }
        worker.join().unwrap().unwrap();
    }

    #[test]
    fn stale_probe_does_not_apply() {
        let mut gate = ProbeGate::default();
        let saved = gate.bump();
        let typed = gate.bump();
        assert!(!gate.is_current(saved));
        assert!(gate.is_current(typed));
    }

    #[test]
    fn shell_does_not_call_webview_navigate() {
        let src = include_str!("lib.rs");
        assert!(
            !src.contains(".navigate("),
            "navigate() fills the Android webview pipe and the process dies"
        );
    }
}
