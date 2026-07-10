# ActiveX proxy to Edge WebView2

This is a pair of ActiveX proxies to [Microsoft Edge WebView2](https://docs.microsoft.com/en-us/microsoft-edge/webview2/) for the [There](https://www.there.com/) client as a replacement for both the [Flash](https://www.adobe.com/products/flashplayer/end-of-life.html) controls and Internet Explorer WebBrowser control.

The [Microsoft Edge WebView2 Runtime](https://developer.microsoft.com/en-us/microsoft-edge/webview2/) needs to be installed to use these controls.

## Building from source (Windows)

The solution `ThereEdge.sln` builds four projects:

| Project | Type | Output |
|---|---|---|
| `FlashProxy` | ATL DLL (C++) | `FlashProxy.dll` |
| `BrowserProxy` | ATL DLL (C++) | `BrowserProxy.dll` |
| `SetupThereEdge` | Python (PyInstaller) | `SetupThereEdge.exe` |
| `Installer` | VS Setup project | `ThereEdge.msi` |

Built against Visual Studio 2022, platform toolset v143, Windows 10 SDK, and
WebView2 NuGet package 1.0.2045.28. You need **one Windows machine** for all of it.

### Step 1 — Install Visual Studio 2022

Get [Visual Studio 2022 Community](https://visualstudio.microsoft.com/vs/) (free)
or any paid edition. During install, in the **Workloads** tab check:

* **Desktop development with C++**
* **Python development**

In the **Installation details → Individual components** tab, make sure these are
checked (C++ workload pulls most in automatically, but confirm):

* **Windows 10 SDK (10.0.19041.0)** — the exact version the projects target
* **MSVC v143 – VS 2022 C++ x64/x86 build tools** (latest)
* **C++ ATL** for latest v143 build tools
* **Python language support**
* **Python 3 64-bit (3.9.13)** — matches the setup helper's `.pyproj`

### Step 2 — Add the Installer Projects extension

The `Installer` project is a legacy `.vdproj` Setup project, which VS 2022 no
longer ships built in. Install the free extension:

* **Extensions → Manage Extensions → Online**, search **"Microsoft Visual Studio
  Installer Projects 2022"**, download, then **close VS to finish the install**.

If you only care about the two DLLs (and not the MSI), you can skip this.

### Step 3 — Get the source and submodules

```bat
git clone --recursive https://github.com/hmphus/there-edge.git
cd there-edge
```

If you already cloned without `--recursive`, init the submodule now:

```bat
git submodule update --init --recursive
```

The `Extras` submodule is required; the resource/version files it carries are
referenced by the build.

### Step 4 — Restore the WebView2 NuGet package

Both C++ projects reference `Microsoft.Web.WebView2` 1.0.2045.28 through a legacy
`packages.config` (not `PackageReference`), so VS must restore it into a local
`packages\` folder before the C++ projects will load.

Easiest way: open `ThereEdge.sln` in Visual Studio. On open, VS offers
**"Restore NuGet Packages"** — click it. Or run from the menu:
**Tools → NuGet Package Manager → Restore NuGet Packages**.

You should now see a `packages\Microsoft.Web.WebView2.1.0.2045.28\` folder.
Without this step the C++ projects fail with *"missing build imports for
Microsoft.Web.WebView2.targets"*.

### Step 5 — (SetupThereEdge only) Install Python deps

The setup helper builds with PyInstaller and uses `pywin32` for COM/shell calls.
From the solution root in a terminal:

```bat
python -m pip install --upgrade pip
pip install pyinstaller pywin32
```

Use the **same** Python 3.9 that VS detected (run `python --version` to confirm
3.9.x; the `.pyproj` calls the `Python` on PATH).

### Step 6 — Choose a configuration and platform

The solution ships three configurations:

* **Debug** — with debug libraries
* **Develop** — intermediate, uses debug libs
* **Release** — what you ship

and two platforms: **Win32** (32-bit, for the 32-bit There client) and **x64**
(64-bit). The There client is 32-bit, so for a drop-in replacement build
**Release | Win32**. Build **both** if you need both client arches.

### Step 7 — Build the solution

In Visual Studio:

1. **Build → Configuration Manager** → set **Active solution configuration** to
   `Release` and **Active solution platform** to `Win32`.
2. **Build → Build Solution** (Ctrl+Shift+B).

Outputs land in the debug/release folders:

* `FlashProxy\Release\FlashProxy.dll` (and Win32/x64 subfolders where configured)
* `BrowserProxy\Release\BrowserProxy.dll`
* `SetupThereEdge\dist\SetupThereEdge.exe`
* `Installer\Release\ThereEdge.msi` (if you built the Installer project)

Or build the pieces you need from a **Developer Command Prompt for VS 2022**:

```bat
:: restore, then build (from solution root)
nuget restore ThereEdge.sln
msbuild ThereEdge.sln /p:Configuration=Release /p:Platform=Win32
```

### Step 8 — Register the DLLs and patch the client

The built DLLs are ActiveX COM servers. To wire them into the There client, run
the setup helper **as Administrator** from the client folder:

```bat
SetupThereEdge.exe --register --patch --path "C:\Program Files (x86)\There\There"
```

What that does:

* `--patch` rewrites the bundled `There.exe` UUIDs into `ThereEdge.exe` so the
  client loads the proxies instead of Flash/IE.
* `--register` runs `regsvr32` on `FlashProxy.dll` and `BrowserProxy.dll`.
* `--startmenu` / `--desktop` create shortcuts to `ThereEdge.exe`.
* `--clean` reverses `--patch` and the shortcuts. `--unregister` reverses
  `--register`. `--pause` keeps the window open on error.

Re-running `--patch` on an already-patched client stops with *"The patch has
already been applied."* — run `--clean` first.

### Step 9 — Update the version (optional, when cutting a release)

Version lives in `Installer\Installer.vdproj` (`ProductVersion`).
`SyncVersion.py` propagates it into the C++ `.rc` files and the Python
`version.py` / `version.rs`. Run it from the solution root after editing the
msi's version:

```bat
python SyncVersion.py
```

### Quick sanity check (any OS, no build needed)

The repo ships a pure-Python self-check that locks two logic fixes against
regression — it parses the C++ source, doesn't compile it, so it runs anywhere:

```bat
python test_selfcheck.py
```

---

### Troubleshooting

* **"references NuGet package(s) that are missing on this computer"** — Step 4
  wasn't done. Run NuGet restore so `packages\Microsoft.Web.WebView2...` exists.
* **Installer project shows as unloaded / won't open** — Step 2 extension
  missing, or VS wasn't restarted after installing it.
* **SetupThereEdge build fails on `win32com` / `pythoncom`** — `pywin32` not
  installed for the Python on PATH (Step 5). Rare install glitch: run
  `python Scripts\pywin32_postinstall.py -install` after installing.
* **Build error about v143 / Windows 10 SDK** — the C++ workload or the
  10.0.19041 SDK wasn't selected in Step 1. Re-run the VS Installer.
* **`--patch` errors "cannot be used with this version of There"** — your There
  client build doesn't match the UUID pairs the patcher expects. You're on your
  own; confirm you're targeting the supported client version.

![Screenshot](https://media.fotki.com/2v2aKZw88x3JhYT.png)
