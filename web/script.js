async function fetchJson(endpoint) {
  const filePath =
    endpoint === "profile"
      ? "data/profile.json"
      : "data/duolingo-progress.json";
  const response = await fetch(filePath);
  if (!response.ok) {
    throw new Error(`Failed to fetch ${filePath}: ${response.statusText}`);
  }
  return response.json();
}

function normalizeProgress(progress) {
  return Object.entries(progress).map(([date, data]) => ({
    date,
    ...data,
  }));
}

function toIsoDate(value) {
  return value.replaceAll("/", "-");
}

function formatDisplayDate(value) {
  const date = new Date(toIsoDate(value));
  const day = String(date.getDate()).padStart(2, "0");
  const month = date.toLocaleDateString("en-US", { month: "short" });
  const year = date.getFullYear();
  return `${day} ${month} ${year}`;
}

function updateProfile(profile) {
  document.getElementById("profile-streak").textContent =
    `${profile.streak} days`;
  document.getElementById("profile-xp").textContent = profile.total_xp;
  document.getElementById("legend-username").textContent =
    `@${profile.username}`;

  const flagsContainer = document.getElementById("profile-language-flags");
  flagsContainer.innerHTML = "";
  profile.languages.forEach((lang) => {
    const img = document.createElement("img");
    img.src = `Images/${lang.name}.svg`;
    img.alt = lang.name;
    img.className = "pill-flag";
    flagsContainer.appendChild(img);
  });
}

function updateWeeklyChart(progress) {
  const today = new Date();
  const last7Days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    return d.toISOString().split("T")[0].replace(/-/g, "/");
  }).reverse();

  const weeklyData = last7Days.map((date) => {
    const dayData = progress.find((p) => p.date === date);
    return { date, xp: dayData ? dayData.xp_today : 0 };
  });

  const maxXp = Math.max(...weeklyData.map((d) => d.xp));
  const chartHeight = 120;
  const chartWidth = 300;

  const line = document.getElementById("weekly-line");
  const dots = document.getElementById("weekly-dots");
  const labels = document.getElementById("weekly-labels");

  const points = [];
  dots.innerHTML = "";
  labels.innerHTML = "";

  let totalXp = 0;
  weeklyData.forEach((d, i) => {
    const x = 40 + (i * chartWidth) / 6;
    const y = 140 - (d.xp / (maxXp || 1)) * chartHeight;
    points.push(`${x},${y}`);

    const circle = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "circle",
    );
    circle.setAttribute("cx", x);
    circle.setAttribute("cy", y);
    circle.setAttribute("r", 3);
    dots.appendChild(circle);

    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", x);
    text.setAttribute("y", 155);
    text.setAttribute("text-anchor", "middle");
    text.textContent = new Date(toIsoDate(d.date)).toLocaleDateString("en-US", {
      weekday: "short",
    });
    labels.appendChild(text);

    totalXp += d.xp;
  });

  line.setAttribute("points", points.join(" "));
  document.getElementById("legend-total").textContent = `${totalXp} XP`;
}

function updateLanguages(profile) {
  const container = document.getElementById("languages-list");
  container.innerHTML = "";
  profile.languages.forEach((lang) => {
    const card = document.createElement("div");
    card.className = "language-card";
    card.innerHTML = `
      <img src="Images/${lang.name}.svg" alt="${lang.name}" class="language-flag">
      <div class="language-name">${lang.name}</div>
      <div class="language-xp">Level ${lang.level}</div>
      <div class="language-xp">${lang.xp} XP</div>
    `;
    container.appendChild(card);
  });
}

function setupFilters(progress, profile) {
  const langFilter = document.getElementById("filter-language");
  langFilter.innerHTML = '<option value="">All Languages</option>';
  profile.languages.forEach((lang) => {
    const option = document.createElement("option");
    option.value = lang.name;
    option.textContent = lang.name;
    langFilter.appendChild(option);
  });

  document
    .getElementById("filter-apply")
    .addEventListener("click", () => updateStats(progress));
  document
    .getElementById("filter-reset")
    .addEventListener("click", () => resetFilters(progress));

  const today = new Date().toISOString().split("T")[0];
  document.getElementById("filter-end").value = today;
  const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
    .toISOString()
    .split("T")[0];
  document.getElementById("filter-start").value = sevenDaysAgo;

  updateStats(progress);
}

function resetFilters(progress) {
  const today = new Date().toISOString().split("T")[0];
  document.getElementById("filter-end").value = today;
  const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
    .toISOString()
    .split("T")[0];
  document.getElementById("filter-start").value = sevenDaysAgo;
  document.getElementById("filter-language").value = "";
  updateStats(progress);
}

function updateStats(progress) {
  const start = document.getElementById("filter-start").value;
  const end = document.getElementById("filter-end").value;

  const filtered = progress.filter((p) => {
    const date = toIsoDate(p.date);
    const dateMatch = date >= start && date <= end;
    return dateMatch;
  });

  const totalXp = filtered.reduce((sum, p) => sum + p.xp_today, 0);
  const sessions = filtered.reduce((sum, p) => sum + p.number_of_sessions, 0);
  const time = filtered.reduce((sum, p) => sum + p.session_time, 0);

  document.getElementById("summary-xp").textContent = totalXp;
  document.getElementById("summary-lessons").textContent = sessions;
  document.getElementById("summary-time").textContent = `${(time / 60).toFixed(
    1,
  )} min`;

  const tableBody = document.getElementById("stats-table-body");
  tableBody.innerHTML = "";
  filtered.forEach((p) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${formatDisplayDate(p.date)}</td>
      <td>${p.number_of_sessions}</td>
      <td>${p.xp_today}</td>
      <td>${(p.session_time / 60).toFixed(1)}</td>
    `;
    tableBody.appendChild(row);
  });
}

async function main() {
  try {
    const [profile, progress] = await Promise.all([
      fetchJson("profile"),
      fetchJson("progress"),
    ]);

    const progressEntries = normalizeProgress(progress);

    updateProfile(profile);
    updateWeeklyChart(progressEntries);
    updateLanguages(profile);
    setupFilters(progressEntries, profile);
  } catch (error) {
    console.error("Error loading DuoStats:", error);
    // Optionally, display an error message to the user
  }
}

main();
