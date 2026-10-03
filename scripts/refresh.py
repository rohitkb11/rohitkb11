"""Generate repository-owned SVGs from public GitHub data; no third-party stats host."""
import collections
import datetime
import html
from html.parser import HTMLParser
import json
import os
import sys
from pathlib import Path
import urllib.request

USER = 'rohitkb11'
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets'


def fetch(url, api=True):
    headers = {'User-Agent': 'rohitkb11-profile-graphics'}
    if api and os.environ.get('GH_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        value = response.read().decode('utf-8')
    return json.loads(value) if api else value


def svg(body, height):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{height}" viewBox="0 0 1000 {height}"><rect width="1000" height="{height}" rx="16" fill="#0d1117" stroke="#303b50"/>{body}</svg>\n'


def text(x, y, value, size=15, color='#8b949e', weight='400'):
    return f'<text x="{x}" y="{y}" font-family="Segoe UI,Arial,sans-serif" font-size="{size}" fill="{color}" font-weight="{weight}">{html.escape(str(value))}</text>'


def stats():
    repos = []
    page = 1
    while True:
        batch = fetch(f'https://api.github.com/users/{USER}/repos?per_page=100&page={page}')
        repos.extend(r for r in batch if not r['fork'])
        if len(batch) < 100:
            break
        page += 1
    languages = collections.Counter()
    for repo in repos:
        languages.update(fetch(repo['languages_url']))
    date = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).strftime('%d %b %Y')
    body = text(30, 40, 'PUBLIC BUILD LOG', 13, '#22d3ee', '600')
    body += text(740, 40, 'Snapshot: ' + date, 13)
    for x, value, label in [(30, len(repos), 'Original public repos'), (270, sum(r['stargazers_count'] for r in repos), 'Repository stars'), (510, sum(r['forks_count'] for r in repos), 'Repository forks')]:
        body += text(x, 100, value, 38, '#f0f6fc', '700') + text(x, 127, label)
    body += text(30, 170, 'CODE MIX', 13, '#a78bfa', '600')
    total = sum(languages.values())
    colors = ['#22d3ee', '#a78bfa', '#34d399', '#fbbf24', '#fb7185', '#60a5fa']
    ranked = languages.most_common(5)
    other = total - sum(value for _, value in ranked)
    if other:
        ranked.append(('Other', other))
    offset = 30.0
    for index, (language, amount) in enumerate(ranked):
        width = amount / total * 940
        body += f'<rect x="{offset:.2f}" y="190" width="{width:.2f}" height="12" fill="{colors[index]}"/>'
        offset += width
        body += text(30 + (index % 3) * 310, 234 + (index // 3) * 30, f'{language}  {amount / total:.1%}', 15, colors[index])
    body += text(30, 299, 'Public non-fork repositories · language bytes, not proficiency', 12)
    (ASSETS / 'stats.svg').write_text(svg(body, 320), encoding='utf-8')


class Calendar(HTMLParser):
    def __init__(self):
        super().__init__()
        self.days = {}

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get('data-date') and values.get('data-level') is not None:
            self.days[values['data-date']] = int(values['data-level'])


def contributions():
    calendar = Calendar()
    source = Path(sys.argv[1]).read_text(encoding='utf-8') if len(sys.argv) > 1 else fetch(f'https://github.com/users/{USER}/contributions', api=False)
    calendar.feed(source)
    if not calendar.days:
        raise RuntimeError('No contribution cells found; keeping previous graphic rather than fabricating activity.')
    dates = sorted(calendar.days)
    first = datetime.date.fromisoformat(dates[0])
    sunday = first - datetime.timedelta(days=(first.weekday() + 1) % 7)
    colors = ['#161e2b', '#123c46', '#136575', '#0891a5', '#22d3ee']
    body = text(30, 35, 'THE CONTRIBUTION TRAIL', 13, '#22d3ee', '600')
    body += text(30, 58, f'Public calendar · {dates[0]} to {dates[-1]}', 12)
    for date, level in sorted(calendar.days.items()):
        delta = (datetime.date.fromisoformat(date) - sunday).days
        x, y = 30 + (delta // 7) * 17.5, 80 + (delta % 7) * 17.5
        body += f'<rect x="{x}" y="{y}" width="13" height="13" rx="3" fill="{colors[level]}"><title>{date}: activity level {level}/4</title></rect>'
    body += '<path d="M30 222H960" stroke="#233047" stroke-width="2"/><circle cx="30" cy="222" r="4" fill="#a78bfa"><animate attributeName="cx" values="30;960;30" dur="18s" repeatCount="indefinite"/></circle>'
    body += text(30, 249, 'Each tile reflects GitHub activity. The moving trail is decorative.', 12)
    (ASSETS / 'contributions.svg').write_text(svg(body, 270), encoding='utf-8')


if __name__ == '__main__':
    ASSETS.mkdir(exist_ok=True)
    stats()
    contributions()
    print('Refreshed stats.svg and contributions.svg from public GitHub data.')
