; TrainConnect Europe – Inno Setup Installer Script
; Erstellt mit Inno Setup 6 (https://jrsoftware.org/isinfo.php)

#define AppName "TrainConnect Europe"
#define AppVersion "1.7.0"
#define AppPublisher "Berner Fachhochschule"
#define AppURL "https://trainconnect.eu"
#define AppExeName "TrainConnect Europe.exe"
#define ElectronExe "electron.exe"

[Setup]
AppId={{E3F8A21C-4B9D-47F2-9E3A-B5C6D8F1A290}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\TrainConnect Europe
DefaultGroupName={#AppName}
AllowNoIcons=no
LicenseFile=LICENSE.txt
OutputDir=dist\installer
OutputBaseFilename=TrainConnect-Europe-Setup-{#AppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
WizardResizable=yes
DisableProgramGroupPage=no
UninstallDisplayIcon={app}\{#AppExeName}

[Languages]
Name: "german";   MessagesFile: "compiler:Languages\German.isl"
Name: "english";  MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";    Description: "{cm:CreateDesktopIcon}";    GroupDescription: "{cm:AdditionalIcons}"
Name: "startmenuicon";  Description: "Startmenü-Verknüpfung";    GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Electron-Kern (alle Dateien aus dem win-build Verzeichnis)
Source: "dist\win-build\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}";       Filename: "{app}\{#ElectronExe}"; AppUserModelID: "eu.trainconnect.app"; Comment: "Pan-europäische Zugbuchungsplattform"
Name: "{group}\{#AppName} deinstallieren"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#ElectronExe}"; AppUserModelID: "eu.trainconnect.app"; Tasks: desktopicon

[Run]
Filename: "{app}\{#ElectronExe}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Registry]
Root: HKCU; Subkey: "Software\TrainConnect"; ValueType: string; ValueName: "InstallDir"; ValueData: "{app}"; Flags: uninsdeletekey

[Code]
// Prüfe ob Port 5000 frei ist (informativ)
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
