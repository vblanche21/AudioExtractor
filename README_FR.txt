AUDIO EXTRACTOR POUR WINDOWS (KIT DE CONSTRUCTION)
=================================================

OBJECTIF
Créer AudioExtractor.exe, un programme Windows autonome avec FFmpeg et
FFprobe inclus. Il permet de sélectionner une vidéo et d'en extraire la
piste audio souhaitée.

INCLUS
- audio_extractor_gui.py       : code source Python de l'interface
- BUILD_WINDOWS.bat            : double-cliquer pour créer le .exe
- build_windows.ps1           : procédure de compilation
- README_PARTAGE.txt          : instructions pour les destinataires
- THIRD_PARTY_NOTICES.txt     : attribution et informations de licence

PRÉREQUIS SUR LE PC QUI CONSTRUIT LE .EXE
- Windows 10/11 64 bits
- Python 3 installé (https://www.python.org/downloads/windows/)
- Connexion Internet lors de la première compilation
- Pas de droits administrateur nécessaires si Python est accessible

MODE D'EMPLOI
1. Décompresser le ZIP de ce kit dans un dossier Windows local.
2. Double-cliquer sur BUILD_WINDOWS.bat.
3. Le script installe PyInstaller dans .venv, récupère FFmpeg/FFprobe
   depuis gyan.dev et contrôle le SHA256 de l'archive téléchargée.
4. Il crée :
     RELEASE\AudioExtractor.exe
     AudioExtractor_Windows_Portable.zip
5. Tester le programme sur une vidéo MKV/MP4.
6. Partager AudioExtractor_Windows_Portable.zip (ou le .exe en conservant
   l'information de licences associée).

IMPORTANT
- Le .exe NE PEUT PAS être compilé directement depuis Linux avec PyInstaller.
- Les destinataires du programme n'ont besoin NI de Python NI de FFmpeg.
- Le .exe est NON SIGNÉ : SmartScreen peut afficher un avertissement.
- Le fichier .exe peut être volumineux (> 100 Mo) car il inclut FFmpeg.
- Pour distribuer un binaire de FFmpeg GPLv3, respecter les obligations
  de redistribution, notamment la disponibilité du code source correspondant.
- FFmpeg est exécuté comme un programme indépendant par l'interface.

DÉPANNAGE
- Python introuvable : installer Python 3 et cocher 'Add Python to PATH'.
- Internet/proxy : le script nécessite de joindre PyPI et gyan.dev.
- Anti-virus : une application PyInstaller non signée peut déclencher une
  détection ; ne pas désactiver la protection pour contourner cela.
- Erreur FFmpeg : consulter la zone 'Informations' du programme.

Les sources sont conservées avec le kit. Ce n'est pas un installateur MSI ;
le résultat est un exécutable portable qui n'écrit aucun fichier système.
