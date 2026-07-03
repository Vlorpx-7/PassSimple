; PassSimple NSIS Installer
; Requires NSIS 3.x + MUI2
; Build from project root: makensis installer\passsimple.nsi

Unicode True

!define PRODUCT_NAME      "PassSimple"
!define PRODUCT_VERSION   "0.3.0"
!define PRODUCT_PUBLISHER "Luca"
!define UNINST_KEY        "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define AUTORUN_KEY       "Software\Microsoft\Windows\CurrentVersion\Run"

; ----------------------------------------------------------------
; MUI2 settings
; ----------------------------------------------------------------
!define MUI_ABORTWARNING
!define MUI_ICON          "..\assets\icon.ico"
!define MUI_UNICON        "..\assets\icon.ico"
!define MUI_FINISHPAGE_RUN      "$INSTDIR\PassSimple.exe"
!define MUI_FINISHPAGE_RUN_TEXT "PassSimple starten"

!include "MUI2.nsh"

; ----------------------------------------------------------------
; General
; ----------------------------------------------------------------
Name    "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "..\build\dist\PassSimple-Setup-${PRODUCT_VERSION}.exe"
InstallDir "$PROGRAMFILES64\${PRODUCT_NAME}"
RequestExecutionLevel admin
SetCompressor /SOLID lzma

; ----------------------------------------------------------------
; Installer pages
; ----------------------------------------------------------------
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\LICENSE"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; ----------------------------------------------------------------
; Uninstaller pages
; ----------------------------------------------------------------
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; ----------------------------------------------------------------
; Languages  (English = primary/default, German = fallback)
; ----------------------------------------------------------------
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "German"

; ----------------------------------------------------------------
; Multilingual strings
; ----------------------------------------------------------------
LangString DESC_SecMain      ${LANG_ENGLISH} "Installs PassSimple and the required files."
LangString DESC_SecMain      ${LANG_GERMAN}  "Installiert PassSimple und die erforderlichen Dateien."
LangString DESC_SecDesktop   ${LANG_ENGLISH} "Creates a shortcut on the Desktop."
LangString DESC_SecDesktop   ${LANG_GERMAN}  "Erstellt eine Verknuepfung auf dem Desktop."
LangString DESC_SecAutostart ${LANG_ENGLISH} "Launches PassSimple automatically at Windows startup."
LangString DESC_SecAutostart ${LANG_GERMAN}  "Startet PassSimple automatisch beim Windows-Start."
LangString MSG_DeleteVault   ${LANG_ENGLISH} "Delete the saved vault as well?$\nAll passwords will be permanently lost."
LangString MSG_DeleteVault   ${LANG_GERMAN}  "Soll auch der gespeicherte Tresor geloescht werden?$\n(Alle Passwoerter gehen verloren)"

; ================================================================
; Installer Sections
; ================================================================

Section "PassSimple" SecMain
  SectionIn RO
  SetRegView 64
  SetOutPath "$INSTDIR"

  File "..\build\dist\PassSimple.exe"
  File /oname=LICENSE.txt "..\LICENSE"
  WriteUninstaller "$INSTDIR\uninstall.exe"

  ; Start menu
  CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
  CreateShortcut "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk" "$INSTDIR\PassSimple.exe"
  CreateShortcut "$SMPROGRAMS\${PRODUCT_NAME}\Uninstall ${PRODUCT_NAME}.lnk" "$INSTDIR\uninstall.exe"

  ; Windows Apps & Features entry
  WriteRegStr   HKLM "${UNINST_KEY}" "DisplayName"     "${PRODUCT_NAME}"
  WriteRegStr   HKLM "${UNINST_KEY}" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegStr   HKLM "${UNINST_KEY}" "DisplayIcon"     "$INSTDIR\PassSimple.exe"
  WriteRegStr   HKLM "${UNINST_KEY}" "Publisher"       "${PRODUCT_PUBLISHER}"
  WriteRegStr   HKLM "${UNINST_KEY}" "DisplayVersion"  "${PRODUCT_VERSION}"
  WriteRegDWORD HKLM "${UNINST_KEY}" "NoModify"        1
  WriteRegDWORD HKLM "${UNINST_KEY}" "NoRepair"        1
SectionEnd

Section "Desktop shortcut" SecDesktop
  CreateShortcut "$DESKTOP\${PRODUCT_NAME}.lnk" "$INSTDIR\PassSimple.exe"
SectionEnd

Section /o "Start with Windows" SecAutostart
  WriteRegStr HKCU "${AUTORUN_KEY}" "${PRODUCT_NAME}" "$INSTDIR\PassSimple.exe"
SectionEnd

; Component page descriptions
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecMain}      $(DESC_SecMain)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop}   $(DESC_SecDesktop)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecAutostart} $(DESC_SecAutostart)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; ================================================================
; Uninstaller Section
; ================================================================

Section "Uninstall"
  SetRegView 64

  Delete "$INSTDIR\PassSimple.exe"
  Delete "$INSTDIR\LICENSE.txt"
  Delete "$INSTDIR\uninstall.exe"
  RMDir  "$INSTDIR"

  Delete "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk"
  Delete "$SMPROGRAMS\${PRODUCT_NAME}\Uninstall ${PRODUCT_NAME}.lnk"
  RMDir  "$SMPROGRAMS\${PRODUCT_NAME}"

  Delete "$DESKTOP\${PRODUCT_NAME}.lnk"

  DeleteRegValue HKCU "${AUTORUN_KEY}" "${PRODUCT_NAME}"
  DeleteRegKey   HKLM "${UNINST_KEY}"

  MessageBox MB_YESNO|MB_ICONQUESTION $(MSG_DeleteVault) IDNO skip_vault_delete
    RMDir /r "$LOCALAPPDATA\PassSimple"
  skip_vault_delete:
SectionEnd
