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
stats_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="460" height="200" viewBox="0 0 460 200">
  <rect width="460" height="200" rx="10" fill="#141321"/>
  <text x="25" y="40" fill="#f8d847" font-family="Arial" font-size="18" font-weight="bold">📊 GitHub Stats</text>
  <text x="25" y="75" fill="#fe428e" font-family="Arial" font-size="28" font-weight="bold">Artem-Kornilov-pro</text>
  <text x="25" y="105" fill="white" font-family="Arial" font-size="14">Commits: {total_commits}</text>
  <text x="25" y="125" fill="white" font-family="Arial" font-size="14">Pull Requests: {total_prs}</text>
  <text x="25" y="145" fill="white" font-family="Arial" font-size="14">Issues: {total_issues}</text>
  <text x="25" y="165" fill="white" font-family="Arial" font-size="14">Stars: {total_stars}  •  Forks: {total_forks}  •  Repos: {total_repos}</text>
</svg>'''

# --- SVG: Языки ---
lang_rows = ""
y = 35
for name, data in sorted_langs:
    pct = round(data["size"] / total_bytes * 100, 1)
    color = data["color"]
    lang_rows += f'''
  <rect x="20" y="{y}" width="420" height="18" rx="3" fill="#2a283e"/>
  <rect x="20" y="{y}" width="{pct * 4.2}" height="18" rx="3" fill="{color}"/>
  <text x="25" y="{y + 13}" fill="white" font-family="Arial" font-size="11">{name} — {pct}%</text>'''
    y += 30

langs_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="460" height="{y + 15}" viewBox="0 0 460 {y + 15}">
  <rect width="460" height="{y + 15}" rx="10" fill="#141321"/>
  <text x="20" y="25" fill="#f8d847" font-family="Arial" font-size="16" font-weight="bold">💻 Top Languages</text>
  {lang_rows}
</svg>'''

with open("github-stats.svg", "w", encoding="utf-8") as f:
    f.write(stats_svg)
with open("github-langs.svg", "w", encoding="utf-8") as f:
    f.write(langs_svg)

cache_buster = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
with open("cache_version.txt", "w") as f:
    f.write(cache_buster)

print(f"✅ SVG files generated! Cache buster: {cache_buster}")
