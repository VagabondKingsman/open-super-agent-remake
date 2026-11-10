//! Which server this phone last opened. The login cookie stays in the webview.

use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Clone, Default, Serialize, Deserialize)]
pub struct Config {
    pub url: Option<String>,
}

fn file(dir: &PathBuf) -> PathBuf {
    let _ = std::fs::create_dir_all(dir);
    dir.join("android.json")
}

pub fn load(dir: &PathBuf) -> Config {
    std::fs::read(file(dir)).ok().and_then(|b| serde_json::from_slice(&b).ok()).unwrap_or_default()
}

pub fn save(dir: &PathBuf, cfg: &Config) {
    if let Ok(b) = serde_json::to_vec_pretty(cfg) {
        let _ = std::fs::write(file(dir), b);
    }
}
