---
date: October 2026
title: EarthScape – GitHub Repository Guide
---

1.  Create a repository on github.com named `EarthScape-Climate-Agency` (Public, no README).
2.  In the project folder:

<!-- -->

    git init
    git add .
    git commit -m "EarthScape Climate Agency – big-data & ML platform"
    git branch -M main
    git remote add origin https://github.com/<your-username>/EarthScape-Climate-Agency.git
    git push -u origin main

3.  The included `.gitignore` excludes the database, model registry, backups and virtual environment.
4.  Files larger than 100 MB are not allowed; `tableau_readings_scored.csv` (≈7.5 MB) and the pickle (≈10 MB) are fine.
5.  Add the repository link to the submission and to `README.md`.
