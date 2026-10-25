fn main() {
    if std::env::var("CARGO_CFG_TARGET_OS").as_deref() == Ok("android") {
        // Keep the library's identity consistent with System.loadLibrary.
        println!("cargo:rustc-link-arg-cdylib=-Wl,-soname,libemi_zenoh_native.so");
    }
}
