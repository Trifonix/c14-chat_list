; Inno Setup script for ChatList.
; Version is passed at build time:
;   iscc /DAppVersion=1.1.0 config\chatlist.iss

#ifndef AppVersion
  #define AppVersion "dev"
#endif

#define AppName "ChatList"
#define AppPublisher "ChatList"
#define AppExeName "chatlist-" + AppVersion + ".exe"
#define AppMutex "ChatList-{#AppVersion}"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputDir=..\dist
OutputBaseFilename={#AppName}-{#AppVersion}-Setup
SetupIconFile=..\app.ico
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\app.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
DisableProgramGroupPage=no
CloseApplications=force
RestartApplications=no

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\app.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\app.ico"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon; IconFilename: "{app}\app.ico"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "taskkill"; Parameters: "/F /IM {#AppExeName}"; Flags: runhidden skipifdoesntexist; RunOnceId: "CloseChatList"

[UninstallDelete]
Type: dirifempty; Name: "{app}\config"
Type: dirifempty; Name: "{app}"

[Code]
var
  DeleteUserData: Boolean;

function IsAppRunning(): Boolean;
var
  ResultCode: Integer;
begin
  if Exec(
    ExpandConstant('{cmd}'),
    '/C tasklist /FI "IMAGENAME eq {#AppExeName}" | find /I "{#AppExeName}" >nul',
    '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    Result := (ResultCode = 0)
  else
    Result := False;
end;

function InitializeUninstall(): Boolean;
begin
  if IsAppRunning() then
  begin
    if MsgBox(
      '{#AppName} сейчас запущен.' + #13#10 +
      'Программа будет закрыта перед удалением.',
      mbInformation, MB_OKCANCEL) = IDCANCEL then
    begin
      Result := False;
      Exit;
    end;
  end;

  if MsgBox(
    'Удалить также пользовательские данные (база данных, логи и .env)?' + #13#10 + #13#10 +
    '«Да» — удалить программу и все данные.' + #13#10 +
    '«Нет» — удалить только файлы программы.',
    mbConfirmation, MB_YESNO) = IDYES then
    DeleteUserData := True
  else
    DeleteUserData := False;

  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep <> usPostUninstall then
    Exit;

  if DeleteUserData then
  begin
    DelTree(ExpandConstant('{app}\data'), True, True, True);
    DeleteFile(ExpandConstant('{app}\config\.env'));
  end;
end;
