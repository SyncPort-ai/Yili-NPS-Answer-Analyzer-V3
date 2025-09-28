Place Chart.js UMD build here as `chart.umd.min.js`.

Recommended file: https://cdn.jsdelivr.net/npm/chart.js/dist/chart.umd.min.js

This project serves static files under `/static`, so the HTML report
will load the library from `/static/thirdparty/chart.umd.min.js`.

Steps:
- Download the file (corp network or offline mirror)
- Save as: nps-report-analyzer/static/thirdparty/chart.umd.min.js

After placing the file, regenerated HTML reports will render charts
without external CDN access.
