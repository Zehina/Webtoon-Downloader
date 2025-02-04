{

  description = "Webtoons Scraper able to download all chapters of any series wanted";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-24.11";
  };

  outputs =
    { nixpkgs, ... }:

    let
      inherit (nixpkgs) lib;

      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];

      packageOf =
        system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        rec {
          default = webtoon-downloader;
          webtoon-downloader = pkgs.callPackage ./package.nix { };
        };
    in

    {
      packages = lib.genAttrs systems packageOf;
    };

}
