# market-news-feed

Fetches recent news headlines for the companies and industries covered on
[exactitudeconsultancy.com](https://exactitudeconsultancy.com), so the website server itself never queries
Google News.

How it works:
1. The website server publishes the day's work list in `queue/today.json` (company search names and industry terms).
2. `.github/workflows/news.yml` splits the list over 8 GitHub machines. Each one asks Google News RSS for one
   item at a time with a 1–2 s random gap, keeps recent headlines that name the company, and stops completely
   at the second "too many requests" reply (the rest goes first in the next run).
3. The results are merged into `results/latest.json.gz` on the `data` branch, which only ever holds the latest
   file. The server downloads it and applies its full filtering rules before anything is shown on the site.

No secrets, credentials or personal data are stored here.
