import json
import os
import requests
import datetime
import sys

USERNAME = "Artem-Kornilov-pro"
TOKEN = os.environ.get("GITHUB_TOKEN")

if not TOKEN:
    print("❌ GITHUB_TOKEN not set!")
    sys.exit(1)

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Упрощённый запрос — меньше шансов на ошибку
query_stats = """
query($username: String!) {
  user(login: $username) {
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      totalCount
      nodes {
        stargazerCount
        forkCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            size
            node {
              name
              color
            }
          }
        }
      }
    }
    pullRequests { totalCount }
    issues { totalCount }
  }
}
"""

def run_query(query):
    try:
        r = requests.post(
            "https://api.github.com/graphql",
            json={"query": query, "variables": {"username": USERNAME}},
            headers=headers,
            timeout=30
        )
        print(f"Status: {r.status_code}")
        if r.status_code != 200:
            print(f"Error: {r.text}")
            sys.exit(1)
        data = r.json()
        if "errors" in data:
            print(f"GraphQL errors: {data['errors']}")
            sys.exit(1)
        return data
    except Exception as e:
        print(f"Request failed: {e}")
        sys.exit(1)

print("Fetching data from GitHub API...")
data = run_query(query_stats)

user = data.get("data", {}).get("user", {})
if not user:
    print("❌ User not found or no data returned")
    sys.exit(1)

contrib = user.get("contributionsCollection", {})

total_commits = contrib.get("totalCommitContributions", 0) + contrib.get("restrictedContributionsCount", 0)
total_prs = user.get("pullRequests", {}).get("totalCount", 0)
total_issues = user.get("issues", {}).get("totalCount", 0)
total_stars = 0
total_forks = 0

# Собираем языки
lang_sizes = {}
repos = user.get("repositories", {})
for repo in repos.get("nodes", []):
    total_stars += repo.get("stargazerCount", 0)
    total_forks += repo.get("forkCount", 0)
    for edge in repo.get("languages", {}).get("edges", []):
        name = edge["node"]["name"]
        size = edge["size"]
        color = edge["node"]["color"] or "#858585"
        if name in lang_sizes:
            lang_sizes[name]["size"] += size
        else:
            lang_sizes[name] = {"size": size, "color": color}

total_repos = repos.get("totalCount", 0)
sorted_langs = sorted(lang_sizes.items(), key=lambda x: x[1]["size"], reverse=True)[:8]
total_bytes = sum(v["size"] for _, v in sorted_langs) or 1

print(f"✅ Data collected: {total_commits} commits, {total_repos} repos, {len(sorted_langs)} languages")

# --- SVG: Статистика ---
stats_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="460" height="200" viewBox="0 0 460 200">
  <rect width="460" height="200" rx="10" fill="#141321"/>
  <text x="25" y="40" fill="#f8d847" font-family="Arial" font-size="18" font-weight="bold">📊 GitHub Stats</text>
  <text x="25" y="75" fill="#fe428e" font-family="Arial" font-size="28" font-weight="bold">{USERNAME}</text>
  <text x="25" y="105" fill="white" font-family="Arial" font-size="14">Total Commits: {total_commits}</text>
  <text x="25" y="125" fill="white" font-family="Arial" font-size="14">Pull Requests: {total_prs}</text>
  <text x="25" y="145" fill="white" font-family="Arial" font-size="14">Issues: {total_issues}</text>
  <text x="25" y="165" fill="white" font-family="Arial" font-size="14">Stars: {total_stars}  •  Forks: {total_forks}  •  Repos: {total_repos}</text>
</svg>'''

# --- SVG: Языки ---
BAR_HEIGHT = 12
BAR_WIDTH = 420
BAR_X = 20
BAR_Y = 55
LEGEND_Y = BAR_Y + BAR_HEIGHT + 22

bar_parts = ""
x_offset = BAR_X
for name, data in sorted_langs:
    pct = data["size"] / total_bytes
    width = max(BAR_WIDTH * pct, 2)  # минимум 2px чтобы было видно
    color = data["color"]
    bar_parts += f'<rect x="{x_offset:.1f}" y="{BAR_Y}" width="{width:.1f}" height="{BAR_HEIGHT}" fill="{color}"/>'
    x_offset += width

legend_parts = ""
legend_x = BAR_X
for name, data in sorted_langs:
    pct = round(data["size"] / total_bytes * 100, 1)
    color = data["color"]

    text_width = len(name) * 7 + 55
    if legend_x + text_width > BAR_X + BAR_WIDTH:
        legend_x = BAR_X
        LEGEND_Y += 20

    legend_parts += f'''
    <circle cx="{legend_x + 5}" cy="{LEGEND_Y - 4}" r="4" fill="{color}"/>
    <text x="{legend_x + 13}" y="{LEGEND_Y}" fill="white" font-family="Arial" font-size="11">{name} {pct}%</text>'''
    legend_x += text_width

total_height = LEGEND_Y + 30

langs_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="460" height="{total_height}" viewBox="0 0 460 {total_height}">
  <rect width="460" height="{total_height}" rx="10" fill="#141321"/>
  <text x="20" y="35" fill="#f8d847" font-family="Arial" font-size="16" font-weight="bold">💻 Top Languages</text>
  <rect x="{BAR_X}" y="{BAR_Y}" width="{BAR_WIDTH}" height="{BAR_HEIGHT}" rx="6" fill="#2a283e"/>
  {bar_parts}
  <rect x="{BAR_X}" y="{BAR_Y}" width="{BAR_WIDTH}" height="{BAR_HEIGHT}" rx="6" fill="none" stroke="#ffffff22" stroke-width="1"/>
  {legend_parts}
</svg>'''

with open("github-stats.svg", "w", encoding="utf-8") as f:
    f.write(stats_svg)
with open("github-langs.svg", "w", encoding="utf-8") as f:
    f.write(langs_svg)

cache_buster = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
with open("cache_version.txt", "w") as f:
    f.write(cache_buster)

print(f"✅ All done! Cache: {cache_buster}")
