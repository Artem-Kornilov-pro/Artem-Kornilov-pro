import json
import os
import requests
import datetime

USERNAME = "Artem-Kornilov-pro"
TOKEN = os.environ.get("GITHUB_TOKEN")

headers = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}

query_stats = """
query($username: String!) {
  user(login: $username) {
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
    }
    repositories(first: 100, ownerAffiliations: OWNER) {
      totalCount
      nodes {
        stargazers { totalCount }
        forkCount
      }
    }
    pullRequests { totalCount }
    issues { totalCount }
  }
}
"""

query_langs = """
query($username: String!) {
  user(login: $username) {
    repositories(first: 100, ownerAffiliations: OWNER) {
      nodes {
        languages(first: 10) {
          edges {
            size
            node { name color }
          }
        }
      }
    }
  }
}
"""

def run_query(query):
    r = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": {"username": USERNAME}},
        headers=headers,
        timeout=30
    )
    if r.status_code != 200:
        print(f"GraphQL error {r.status_code}: {r.text}")
        raise SystemExit(1)
    return r.json()

stats = run_query(query_stats)
langs = run_query(query_langs)

user = stats.get("data", {}).get("user", {})
contrib = user.get("contributionsCollection", {})

total_commits = contrib.get("totalCommitContributions", 0) + contrib.get("restrictedContributionsCount", 0)
total_prs = user.get("pullRequests", {}).get("totalCount", 0)
total_issues = user.get("issues", {}).get("totalCount", 0)
total_stars = 0
total_forks = 0

repos_data = user.get("repositories", {})
for repo in repos_data.get("nodes", []):
    total_stars += repo.get("stargazers", {}).get("totalCount", 0)
    total_forks += repo.get("forkCount", 0)
total_repos = repos_data.get("totalCount", 0)

lang_sizes = {}
for repo in langs.get("data", {}).get("user", {}).get("repositories", {}).get("nodes", []):
    for edge in repo.get("languages", {}).get("edges", []):
        name = edge["node"]["name"]
        size = edge["size"]
        color = edge["node"]["color"]
        if name in lang_sizes:
            lang_sizes[name]["size"] += size
        else:
            lang_sizes[name] = {"size": size, "color": color}

sorted_langs = sorted(lang_sizes.items(), key=lambda x: x[1]["size"], reverse=True)[:8]
total_bytes = sum(v["size"] for _, v in sorted_langs) or 1

# --- SVG: Статистика ---
# --- SVG: Языки (одна полоса + легенда) ---
BAR_HEIGHT = 12
BAR_WIDTH = 420
BAR_X = 20
BAR_Y = 60
LEGEND_Y = BAR_Y + BAR_HEIGHT + 25

# Полоса
bar_parts = ""
legend_parts = ""
legend_x = BAR_X
x_offset = BAR_X

for name, data in sorted_langs:
    pct = data["size"] / total_bytes
    width = BAR_WIDTH * pct
    color = data["color"]
    bar_parts += f'<rect x="{x_offset:.1f}" y="{BAR_Y}" width="{width:.1f}" height="{BAR_HEIGHT}" fill="{color}"/>'
    x_offset += width

# Легенда (кругляши + подписи)
legend_x = BAR_X
for name, data in sorted_langs:
    pct = round(data["size"] / total_bytes * 100, 1)
    color = data["color"]

    # Перенос строки, если не влезает
    if legend_x > BAR_X + BAR_WIDTH - 80:
        legend_x = BAR_X
        LEGEND_Y += 20

    legend_parts += f'''
    <circle cx="{legend_x + 5}" cy="{LEGEND_Y - 4}" r="4" fill="{color}"/>
    <text x="{legend_x + 13}" y="{LEGEND_Y}" fill="white" font-family="Arial" font-size="11">{name} {pct}%</text>'''
    legend_x += len(name) * 7 + 50  # примерный отступ

total_height = LEGEND_Y + 30

langs_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="460" height="{total_height}" viewBox="0 0 460 {total_height}">
  <rect width="460" height="{total_height}" rx="10" fill="#141321"/>
  <text x="20" y="35" fill="#f8d847" font-family="Arial" font-size="16" font-weight="bold">💻 Top Languages</text>

  <!-- Цветная полоса -->
  <rect x="{BAR_X}" y="{BAR_Y}" width="{BAR_WIDTH}" height="{BAR_HEIGHT}" rx="6" fill="#2a283e"/>
  {bar_parts}
  <rect x="{BAR_X}" y="{BAR_Y}" width="{BAR_WIDTH}" height="{BAR_HEIGHT}" rx="6" fill="none" stroke="#ffffff22" stroke-width="1"/>

  <!-- Легенда -->
  {legend_parts}
</svg>'''

with open("github-stats.svg", "w", encoding="utf-8") as f:
    f.write(stats_svg)
with open("github-langs.svg", "w", encoding="utf-8") as f:
    f.write(langs_svg)

cache_buster = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
with open("cache_version.txt", "w") as f:
    f.write(cache_buster)

print(f"✅ SVG files generated! Cache buster: {cache_buster}")
