# AudioExtractor

Application Windows gratuite pour extraire une piste audio de vidéos MKV, MP4, AVI, MOV et WebM avec FFmpeg.

## Fonctionnalités

- Détection des pistes audio (langue, codec, canaux, selon les métadonnées).
- Extraction sans réencodage vers un fichier `.mka`.
- Conversion en MP3, WAV ou FLAC.
- Interface graphique en français.
- Fonctionnement local, sans compte, sans transfert de vos vidéos.

## Télécharger

La version portable Windows sera disponible dans la rubrique **Releases** une fois publiée. Pour l'instant, le code source et les scripts de compilation sont en cours de publication.

## Compiler sous Windows

1. Installer Python 3.
2. Télécharger les sources du dépôt.
3. Exécuter `BUILD_WINDOWS.bat`.
4. Récupérer `AudioExtractor_Windows_Portable.zip`.

Le script de construction récupère FFmpeg et FFprobe, et compile avec PyInstaller.

## Licences

Code de l'interface : MIT, voir `LICENSE` (à ajouter). FFmpeg est une dépendance tierce dont les obligations de redistribution dépendent de sa compilation et de sa licence (GPL/LGPL). Ne pas diffuser les binaires FFmpeg sans les mentions et le code source correspondant requis.

## Sécurité

Aucune vidéo n'est envoyée sur Internet. L'exécutable non signé peut provoquer un avertissement Windows SmartScreen.
