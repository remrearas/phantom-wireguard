fn main() {
    // Link against libnftables (system library)
    // Requires: apt-get install libnftables-dev
    println!("cargo:rustc-link-lib=nftables");
}
