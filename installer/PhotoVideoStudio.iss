#define MyAppName "Photo Video Studio"
#define MyAppPublisher "Kingprogrammer07"
#define MyAppExeName "PhotoVideoStudio.exe"

#ifndef AppVersion
#define AppVersion "0.0.0"
#endif

#ifndef SourceDir
#define SourceDir "..\dist\PhotoVideoStudio"
#endif

[Setup]
AppId={{5D18D55D-315B-47A4-8628-EAE8B9C62258}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://github.com/Kingprogrammer07/photo_video_studio
AppSupportURL=https://github.com/Kingprogrammer07/photo_video_studio/issues
AppUpdatesURL=https://github.com/Kingprogrammer07/photo_video_studio/releases
DefaultDirName={localappdata}\Programs\Photo Video Studio
DefaultGroupName=Photo Video Studio
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\release
OutputBaseFilename=PhotoVideoStudioSetup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes
PrivilegesRequired=lowest

[Languages]
Name: "uzbek"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Ish stoliga belgi qo'yish"; GroupDescription: "Qo'shimcha belgilar:"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Photo Video Studio"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Photo Video Studio"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Photo Video Studio'ni ishga tushirish"; Flags: nowait postinstall skipifsilent

[Code]
function HasInternet(): Boolean;
var
  Http: Variant;
begin
  Result := False;
  try
    Http := CreateOleObject('WinHttp.WinHttpRequest.5.1');
    Http.SetTimeouts(3000, 3000, 5000, 5000);
    Http.Open('GET', 'https://api.github.com', False);
    Http.Send('');
    Result := (Http.Status >= 200) and (Http.Status < 500);
  except
    Result := False;
  end;
end;

function InitializeSetup(): Boolean;
begin
  Result := HasInternet();
  if not Result then
  begin
    MsgBox('O''rnatish uchun internet kerak. O''rnatilgandan keyin Photo Video Studio video va konvertatsiya funksiyalarida internetsiz ham ishlaydi. AI funksiyalari uchun internet kerak bo''ladi.', mbError, MB_OK);
  end;
end;
