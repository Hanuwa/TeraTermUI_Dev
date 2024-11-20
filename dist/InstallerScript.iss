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
LicenseFile={#MyAppPath}/TeraTermUI_installer/LICENSE.txt
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputBaseFilename=TeraTermUI_64-bit_Installer-
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=tera-term.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages/Spanish.isl"

[CustomMessages]
english.teraterm=To utilize 'Tera Term UI', 'Tera Term' needs to be installed. Would you like to install 'Tera Term' now as part of this setup?
spanish.teraterm=Para utilizar 'Tera Term UI', es necesario tener instalado 'Tera Term'. ¿Desea instalar 'Tera Term' ahora como parte de esta configuración?
english.AdminPrivilegesRequired=Administrative privileges are required to install for all users. Please restart the installer with admin rights.
spanish.AdminPrivilegesRequired=Se requieren privilegios administrativos para instalar para todos los usuarios. Por favor, reinicie el instalador con derechos de administrador.
english.TeraTermInstallFailed=Tera Term installation failed.
spanish.TeraTermInstallFailed=La instalación de Tera Term falló.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "teraterm"; Description: "{cm:teraterm}"; GroupDescription: "Additional installations"; Flags: unchecked

[Files]
Source: "{#MyAppPath}/TeraTermUI_installer/{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyAppPath}/database.db"; DestDir: "{code:GetDataDir}"; Flags: external; Check: ShouldUpdateFile(ExpandConstant('{code:GetDataDir}/database.db'), ExpandConstant('{#MyAppPath}/database.db')); Permissions: everyone-modify
Source: "{#MyAppPath}/feedback.zip"; DestDir: "{code:GetDataDir}"; Flags: external; Check: ShouldUpdateFile(ExpandConstant('{code:GetDataDir}/feedback.zip'), ExpandConstant('{#MyAppPath}/feedback.zip')); Permissions: everyone-modify
Source: "{#MyAppPath}/updater.exe"; DestDir: "{code:GetDataDir}"; Flags: external; Check: ShouldUpdateFile(ExpandConstant('{code:GetDataDir}/updater.exe'), ExpandConstant('{#MyAppPath}/updater.exe')); Permissions: everyone-modify
Source: "{#MyAppPath}/TeraTermUI_installer/*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#MyAppPath}/teraterm-4.108.exe"; DestDir: "{tmp}"; Flags: ignoreversion; Tasks: teraterm
Source: "C:/Program Files/Git/usr/bin/md5sum.exe"; DestDir: "{tmp}"; Flags: ignoreversion

[UninstallDelete]
Type: filesandordirs; Name: "{code:GetDataDir}"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}/{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}/{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}/{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    if WizardIsTaskSelected('teraterm') then
    begin
      if not Exec(ExpandConstant('{tmp}/teraterm-4.108.exe'), '/SILENT', '', SW_SHOW, ewWaitUntilTerminated, ResultCode) then
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
    Result := ExpandConstant('{commonpf64}/TeraTermUI') 
  else
    Result := ExpandConstant('{localappdata}/Programs/TeraTermUI');
end;

function GetDataDir(Default: string): string;
begin
  if IsAdminInstallMode then
    Result := ExpandConstant('{commonappdata}/TeraTermUI') 
  else
    Result := ExpandConstant('{userappdata}/TeraTermUI');
end;

function GetMD5Hash(const FileName: string): string;
var
  ResultCode: Integer;
  OutputFile: string;
  OutputLines: TArrayOfString;
begin
  Result := ''; 
  if not FileExists(FileName) then
    Exit;

  OutputFile := ExpandConstant('{tmp}\md5output.txt');
  if Exec(ExpandConstant('{tmp}\md5sum.exe'), '"' + FileName + '" > "' + OutputFile + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    if (ResultCode = 0) and FileExists(OutputFile) then
    begin
      LoadStringsFromFile(OutputFile, OutputLines);
      if GetArrayLength(OutputLines) > 0 then
        Result := Copy(OutputLines[0], 1, Pos(' ', OutputLines[0]) - 1); 
    end;
  end;
  if FileExists(OutputFile) then
    DeleteFile(OutputFile); 
end;

function ShouldUpdateFile(DestFile: string; SourceFile: string): Boolean;
var
  DestHash, SourceHash: string;
begin
  Result := True; 
  if FileExists(DestFile) then
  begin
    DestHash := GetMD5Hash(DestFile);
    SourceHash := GetMD5Hash(SourceFile);
    Result := DestHash <> SourceHash; 
  end;
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
  TempDir, TeraTermUITempDir, TesseractOCRDir, INIFilePath: string;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    TempDir := GetTempDir;
    TeraTermUITempDir := AddBackslash(TempDir) + 'TeraTermUI';
    TesseractOCRDir := AddBackslash(TeraTermUITempDir) + 'Tesseract-OCR';
    INIFilePath := TeraTermUITempDir + 'TERATERM.ini.bak';

    if DirExists(TeraTermUITempDir) then
    begin
      if FileExists(INIFilePath) then
      begin
        if DirExists(TesseractOCRDir) then
        begin
          DelTree(TesseractOCRDir, True, True, True);
        end;
      end
      else
      begin
        DelTree(TeraTermUITempDir, True, True, True);
      end;
    end;
  end;
end;
