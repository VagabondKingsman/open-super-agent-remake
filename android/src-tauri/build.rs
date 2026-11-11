fn main() {
    tauri_build::try_build(
        tauri_build::Attributes::new().app_manifest(
            tauri_build::AppManifest::new().commands(&[
                "setup_state",
                "choose_remote",
                "confirm_pair",
                "cancel_pair",
                "android_open_external",
                "android_switch_server",
                "android_open_sheet",
                "android_set_badge",
            ]),
        ),
    )
    .expect("failed to build tauri context");
}
