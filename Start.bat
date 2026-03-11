cd src
color 2
ECHO OFF
title Webtoon Downloader
mode con:cols=64 lines=32

:Home
@if exist Properties.dat (< Properties.dat (set /p dest=)) ELSE (set dest=./Downloaded)
CLS
echo.
echo.
echo.
echo.
echo      ######################################################     
echo      #"               ___  __  ___  __   __              "#     
echo      #"         |  | |__  |__)  |  /  \ /  \ |\ |        "#     
echo      #"         |/\| |___ |__)  |  \__/ \__/ | \|        "#     
echo      #"                                                  "#     
echo      #" __   __                  __        __   ___  __  "#     
echo      #"|  \ /  \ |  | |\ | |    /  \  /\  |  \ |__  |__) "#     
echo      #"|__/ \__/ |/\| | \| |___ \__/ /~~\ |__/ |___ |  \ "#   
echo      #"                                                  "#   
echo      #" [built by: Zehina]        [Interface by: kekuwi] "#     
echo      ######################################################     
ECHO.
ECHO.
ECHO.
ECHO 	Select a downlaod option: [1] Latest Chapter Only
ECHO 				  [2] All Chapter
ECHO 				  [3] Start from Chapter
ECHO 				  [4] End until Chapter
ECHO 				  [5] Between Chapter
ECHO 				  [6] Settings
ECHO 				  [0] Exit
choice /c 1234560 /n


:: Note - list ERRORLEVELS in decreasing order
IF ERRORLEVEL 7 GOTO exit
IF ERRORLEVEL 6 GOTO Setting
IF ERRORLEVEL 5 GOTO between
IF ERRORLEVEL 4 GOTO enduntil
IF ERRORLEVEL 3 GOTO startfrom
IF ERRORLEVEL 2 GOTO all
IF ERRORLEVEL 1 GOTO latest

:latest
CLS
echo.
echo.
echo.
echo.
echo      ######################################################     
echo      #"               ___  __  ___  __   __              "#     
echo      #"         |  | |__  |__)  |  /  \ /  \ |\ |        "#     
echo      #"         |/\| |___ |__)  |  \__/ \__/ | \|        "#     
echo      #"                                                  "#     
echo      #" __   __                  __        __   ___  __  "#     
echo      #"|  \ /  \ |  | |\ | |    /  \  /\  |  \ |__  |__) "#     
echo      #"|__/ \__/ |/\| | \| |___ \__/ /~~\ |__/ |___ |  \ "#   
echo      #"                                                  "#   
echo      #" [built by: Zehina]        [Interface by: kekuwi] "#     
echo      ######################################################     
ECHO.
ECHO.
ECHO.
ECHO Download Location: %dest%
set /p URL=Webtoon Url:
@python webtoon_downloader.py %URL% --latest

pause
GOTO Home

:all
CLS
echo.
echo.
echo.
echo.
echo      ######################################################     
echo      #"               ___  __  ___  __   __              "#     
echo      #"         |  | |__  |__)  |  /  \ /  \ |\ |        "#     
echo      #"         |/\| |___ |__)  |  \__/ \__/ | \|        "#     
echo      #"                                                  "#     
echo      #" __   __                  __        __   ___  __  "#     
echo      #"|  \ /  \ |  | |\ | |    /  \  /\  |  \ |__  |__) "#     
echo      #"|__/ \__/ |/\| | \| |___ \__/ /~~\ |__/ |___ |  \ "#   
echo      #"                                                  "#   
echo      #" [built by: Zehina]        [Interface by: kekuwi] "#     
echo      ######################################################     
ECHO.
ECHO.
ECHO.
ECHO Download Location: %dest%
set /p URL=Webtoon Url:
@python webtoon_downloader.py %URL% --seperate --dest %dest%

:startfrom
CLS
echo.
echo.
echo.
echo.
echo      ######################################################     
echo      #"               ___  __  ___  __   __              "#     
echo      #"         |  | |__  |__)  |  /  \ /  \ |\ |        "#     
echo      #"         |/\| |___ |__)  |  \__/ \__/ | \|        "#     
echo      #"                                                  "#     
echo      #" __   __                  __        __   ___  __  "#     
echo      #"|  \ /  \ |  | |\ | |    /  \  /\  |  \ |__  |__) "#     
echo      #"|__/ \__/ |/\| | \| |___ \__/ /~~\ |__/ |___ |  \ "#   
echo      #"                                                  "#   
echo      #" [built by: Zehina]        [Interface by: kekuwi] "#     
echo      ######################################################     
ECHO.
ECHO.
ECHO.
ECHO Download Location: %dest%
set /p URL=Webtoon Url:
set /p SPage=Starting Page:
@python webtoon_downloader.py %URL% --start %Spage% --seperate --dest %dest%

pause
GOTO Home

:enduntil
CLS
echo.
echo.
echo.
echo.
echo      ######################################################     
echo      #"               ___  __  ___  __   __              "#     
echo      #"         |  | |__  |__)  |  /  \ /  \ |\ |        "#     
echo      #"         |/\| |___ |__)  |  \__/ \__/ | \|        "#     
echo      #"                                                  "#     
echo      #" __   __                  __        __   ___  __  "#     
echo      #"|  \ /  \ |  | |\ | |    /  \  /\  |  \ |__  |__) "#     
echo      #"|__/ \__/ |/\| | \| |___ \__/ /~~\ |__/ |___ |  \ "#   
echo      #"                                                  "#   
echo      #" [built by: Zehina]        [Interface by: kekuwi] "#     
echo      ######################################################     
ECHO.
ECHO.
ECHO.
ECHO Download Location: %dest%
set /p URL=Webtoon Url:
set /p EPage=Starting Page:
@python webtoon_downloader.py %URL% --end %page% --seperate --dest %dest%

pause
GOTO Home

:between
CLS
echo.
echo.
echo.
echo.
echo      ######################################################     
echo      #"               ___  __  ___  __   __              "#     
echo      #"         |  | |__  |__)  |  /  \ /  \ |\ |        "#     
echo      #"         |/\| |___ |__)  |  \__/ \__/ | \|        "#     
echo      #"                                                  "#     
echo      #" __   __                  __        __   ___  __  "#     
echo      #"|  \ /  \ |  | |\ | |    /  \  /\  |  \ |__  |__) "#     
echo      #"|__/ \__/ |/\| | \| |___ \__/ /~~\ |__/ |___ |  \ "#   
echo      #"                                                  "#   
echo      #" [built by: Zehina]        [Interface by: kekuwi] "#     
echo      ######################################################     
ECHO.
ECHO.
ECHO.
ECHO Download Location: %dest%
set /p URL=Webtoon Url:
set /p SPage=Starting Page:
set /p EPage=End Page:
@python webtoon_downloader.py %URL% --end %page% --seperate --dest %dest%

pause
GOTO Home

:Setting
CLS
echo.
echo.
echo.
echo.
echo      ######################################################     
echo      #"               ___  __  ___  __   __              "#     
echo      #"         |  | |__  |__)  |  /  \ /  \ |\ |        "#     
echo      #"         |/\| |___ |__)  |  \__/ \__/ | \|        "#     
echo      #"                                                  "#     
echo      #" __   __                  __        __   ___  __  "#     
echo      #"|  \ /  \ |  | |\ | |    /  \  /\  |  \ |__  |__) "#     
echo      #"|__/ \__/ |/\| | \| |___ \__/ /~~\ |__/ |___ |  \ "#   
echo      #"                                                  "#   
echo      #" [built by: Zehina]        [Interface by: kekuwi] "#     
echo      ######################################################     
ECHO.
ECHO.
ECHO.
ECHO  		   Settings: [1] Download Path
ECHO 			     [0] Back

choice /c 01 /n

IF ERRORLEVEL 2 GOTO DownloadPath
IF ERRORLEVEL 1 GOTO Home

:DownloadPath
CLS
echo.
echo.
echo.
echo.
echo      ######################################################     
echo      #"               ___  __  ___  __   __              "#     
echo      #"         |  | |__  |__)  |  /  \ /  \ |\ |        "#     
echo      #"         |/\| |___ |__)  |  \__/ \__/ | \|        "#     
echo      #"                                                  "#     
echo      #" __   __                  __        __   ___  __  "#     
echo      #"|  \ /  \ |  | |\ | |    /  \  /\  |  \ |__  |__) "#     
echo      #"|__/ \__/ |/\| | \| |___ \__/ /~~\ |__/ |___ |  \ "#   
echo      #"                                                  "#   
echo      #" [built by: Zehina]        [Interface by: kekuwi] "#     
echo      ######################################################     
ECHO.
ECHO.
ECHO.
ECHO Current Download Location: %dest%
set /p dest=Set download Path:
(
ECHO %dest%\Downloaded
) > Properties.dat
GOTO Home

:exit
@exit