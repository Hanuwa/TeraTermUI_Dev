#define MyAppName "Tera Term UI"
#define MyAppVersion 
#define MyAppPublisher "Armando Del Valle Tejada"
#define MyAppURL "github.com/Hanuwa/TeraTermUI"
#define MyAppExeName "TeraTermUI.exe"
#define MyAppPath 

[Setup]
AppId={{FFAC4B8F-D556-4D37-AA80-246FBE4CB5A1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
VersionInfoVersion={#MyAppVersion}
ArchitecturesInstallIn64BitMode=x64compatible
AppVerName={#MyAppName}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={code:GetInstallDir}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile={#MyAppPath}\TeraTermUI_installer\LICENSE.txt
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputBaseFilename=TeraTermUI_64-bit_Installer-
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=tera-term.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[CustomMessages]
english.teraterm=To utilize 'Tera Term UI', 'Tera Term' needs to be installed. Would you like to install 'Tera Term' now as part of this setup?
spanish.teraterm=Para utilizar 'Tera Term UI', es necesario tener instalado 'Tera Term'. ¿Desea instalar 'Tera Term' ahora como parte de esta configuración?
english.AdminPrivilegesRequired=Administrative privileges are required to install for all users. Please restart the installer with admin rights.
spanish.AdminPrivilegesRequired=Se requieren privilegios administrativos para instalar para todos los usuarios. Por favor, reinicie el instalador con derechos de administrador.
english.TeraTermInstallFailed=Tera Term installation failed.
spanish.TeraTermInstallFailed=La instalación de Tera Term falló.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "teraterm"; Description: "{cm:teraterm}"; GroupDescription: "Additional installations"; Flags: unchecked

[Files]
Source: "{#MyAppPath}\TeraTermUI_installer\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyAppPath}\database.db"; DestDir: "{code:GetDataDir}"; Flags: onlyifdoesntexist; Permissions: everyone-modify
Source: "{#MyAppPath}\feedback.zip"; DestDir: "{code:GetDataDir}"; Flags: onlyifdoesntexist; Permissions: everyone-modify
Source: "{#MyAppPath}\updater.exe"; DestDir: "{commonappdata}\TeraTermUI"; Flags: onlyifdoesntexist; Permissions: everyone-modify
Source: "{#MyAppPath}\TeraTermUI_installer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#MyAppPath}\teraterm-4.108.exe"; DestDir: "{tmp}"; Flags: ignoreversion; Tasks: teraterm

[UninstallDelete]
Type: filesandordirs; Name: "{code:GetDataDir}"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    if WizardIsTaskSelected('teraterm') then
    begin
      if not Exec(ExpandConstant('{tmp}\teraterm-4.108.exe'), '/SILENT', '', SW_SHOW, ewWaitUntilTerminated, ResultCode) then
      begin
        MsgBox(ExpandConstant('{cm:TeraTermInstallFailed}'), mbError, MB_OK);
      end
      else if ResultCode <> 0 then
      begin
        MsgBox(ExpandConstant('{cm:TeraTermInstallFailed}') + ' Error Code: ' + IntToStr(ResultCode), mbError, MB_OK);
      end;
    end;
  end;
end;

const
  ComtypesCacheDirName = 'comtypes_cache';
  TeraTermUIDirPrefix = 'TeraTermUI-';
function IsDirectoryEmpty(const DirPath: string): Boolean;
var
  FindRec: TFindRec;
begin
  Result := True;
  if FindFirst(DirPath + '*', FindRec) then
  begin
    try
      repeat
        if (FindRec.Name <> '.') and (FindRec.Name <> '..') then
        begin
          Result := False;
          Break;
        end;
      until not FindNext(FindRec);
    finally
      FindClose(FindRec);
    end;
  end;
end;

function GetInstallDir(Default: string): string;
begin
  if IsAdminInstallMode then
    Result := ExpandConstant('{commonpf64}\TeraTermUI') 
  else
    Result := ExpandConstant('{localappdata}\Programs\TeraTermUI');
end;

function GetDataDir(Default: string): string;
begin
  if IsAdminInstallMode then
    Result := ExpandConstant('{commonappdata}\TeraTermUI}') 
  else
    Result := ExpandConstant('{userappdata}\TeraTermUI');
end;


procedure DeleteTeraTermUIDirectories(const ParentDir: string);
var
  FindRec: TFindRec;
  SubDirName: string;
begin
  if FindFirst(ParentDir + '*', FindRec) then
  begin
    try
      repeat
        if ((FindRec.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0) and 
           (FindRec.Name <> '.') and (FindRec.Name <> '..') and 
           (Pos(TeraTermUIDirPrefix, FindRec.Name) = 1) then
        begin
          SubDirName := ParentDir + FindRec.Name;
          DelTree(SubDirName, True, True, True);
        end;
      until not FindNext(FindRec);
    finally
      FindClose(FindRec);
    end;
  end;
  if IsDirectoryEmpty(ParentDir) then
  begin
    RemoveDir(ParentDir);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  TempDir, ComtypesCacheDir: string;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    TempDir := GetTempDir;
    ComtypesCacheDir := AddBackslash(TempDir) + ComtypesCacheDirName;
    if DirExists(ComtypesCacheDir) then
    begin
      DeleteTeraTermUIDirectories(AddBackslash(ComtypesCacheDir));
    end;
  end;
end;
