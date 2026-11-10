//! Address and pairing rules for the Android shell.
//! The shell does not run OSA. It opens the server's own web UI.

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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bare_host_becomes_https_origin() {
        let u = normalize("osa.example.com/apps").unwrap();
        assert_eq!(u.as_str(), "https://osa.example.com/");
    }

    #[test]
    fn explicit_http_stays_http() {
        let u = normalize("http://192.168.1.10:8765").unwrap();
        assert_eq!(u.as_str(), "http://192.168.1.10:8765/");
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
    fn bad_ticket_is_dropped() {
        let u = Url::parse("opensuperagent://pair?u=https://osa.example.com&t=a.b").unwrap();
        assert!(parse_pair(&u).is_none());
    }

}
