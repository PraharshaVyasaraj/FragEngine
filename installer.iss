; Inno Setup Script for FragEngine Standalone Spectator Addon
; Generates a guided installation wizard with uninstaller and shortcuts.

[Setup]
AppName=FragEngine Spectator Addon
AppVersion=0.16.0
DefaultDirName={pf}\FragEngine
DefaultGroupName=FragEngine
OutputBaseFilename=FragEngine_Spectator_Addon_Setup
Compression=lzma
SolidCompression=yes
OutputDir=dist_setup
PrivilegesRequired=none
SetupIconFile=dist\FragEngine_Spectator_Addon\FragEngine_Spectator_Addon.exe
UninstallDisplayIcon={app}\FragEngine_Spectator_Addon.exe

[Files]
; Copy PyInstaller compiled binary folder
Source: "dist\FragEngine_Spectator_Addon\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs
; Copy local ruleset configuration folders
Source: "config\rulesets\*"; DestDir: "{app}\config\rulesets"; Flags: recursesubdirs createallsubdirs
Source: "icons\*"; DestDir: "{app}\icons"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\FragEngine Spectator Addon"; Filename: "{app}\FragEngine_Spectator_Addon.exe"
Name: "{commondesktop}\FragEngine Spectator Addon"; Filename: "{app}\FragEngine_Spectator_Addon.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
Filename: "{app}\FragEngine_Spectator_Addon.exe"; Description: "Launch FragEngine Spectator Addon"; Flags: nowait postinstall skipifsilent
