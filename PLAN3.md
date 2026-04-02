# PLAN3: Page Consolidation — 30 Pages Down to 8

## Problem

The app has **30 sidebar items** and **36 total pages**. Users must navigate through too many separate pages to find features. Many pages share the same pattern (movie grid + filters) and can be combined under one roof with tabs.

## Goal

Reduce sidebar navigation to **8 items** (down from 30) without losing a single feature. All current functionality remains accessible via **tabs within consolidated pages**. The same 8 navigation items appear in both the sidebar and the top nav bar.

---

## Consolidation Map

### Current (30 sidebar items) → New (8 sidebar items)

| New Page | Absorbs These Current Pages | Navigation Pattern |
|----------|----------------------------|-------------------|
| **Home** | Home (unchanged) | Landing page |
| **Discover** | Discover, Trending, Top Charts, Hidden Gems, Seasonal, Controversial, Decades | Tabs across the top |
| **Search** | Search, Moods, AdvancedSearch | Mode toggle (Title / Vibe & Mood / Advanced) |
| **Explore** | Directors, Actors, Cast Combo, Keywords | Tabs across the top |
| **For You** | Recommendations, Blind Spots, Rewatch | Tabs across the top |
| **Library** | Watchlist, My Lists, Collections, Director Gaps, Curated | Tabs across the top |
| **Activity** | Achievements, Challenges, Bingo, Diary | Tabs across the top |
| **Profile** | Profile, Taste Evolution, Platform Stats | Tabs/sections |

**Pages that remain as standalone routes (no sidebar entry):** Onboarding, MovieDetail, FromSeedRecommendations, WatchlistRecommendations, ListDetail, PopularLists, Compare

**Compare** is accessible from MovieDetail and via direct URL — it doesn't need a sidebar entry.

---

## Detailed Breakdown

### 1. Home (`/`)
**No changes.** Stays as the personalized landing page with carousels, mood selector, surprise picks, feed sections, etc.

---

### 2. Discover (`/discover`)
**Merges 7 pages into one with a tab bar.**

| Tab | Old Page | Route |
|-----|----------|-------|
| Browse | Discover | `/discover` or `/discover/browse` |
| Trending | Trending | `/discover/trending` |
| Top Charts | TopCharts | `/discover/top-charts` |
| Hidden Gems | HiddenGems | `/discover/hidden-gems` |
| Seasonal | Seasonal | `/discover/seasonal` |
| Controversial | Controversial | `/discover/controversial` |
| Decades | Decades | `/discover/decades` |

**Implementation:**
- Create a shared `DiscoverLayout` wrapper with a horizontal tab bar at the top
- Each tab renders the existing page component's content (the inner content, without the layout wrapper)
- The "Browse" tab is the default (the current Discover page with genre/year/language/runtime filters)
- URL changes when switching tabs for deep-linking and browser back support
- Each tab keeps its own filter state independently

---

### 3. Search (`/search`)
**Merges 3 pages into one with a mode switcher.**

| Mode | Old Page | Description |
|------|----------|-------------|
| Title Search | Search | Standard text search with fuzzy matching |
| Vibe & Mood | Moods | Semantic search + mood presets/pills |
| Advanced | AdvancedSearch | Multi-criteria filters (director, keyword, cast, rating, runtime, genre, decade, language) |

**Implementation:**
- Single page with a segmented control / pill toggle at the top: `Title | Vibe & Mood | Advanced`
- Title mode: search input + results grid (current Search page)
- Vibe & Mood mode: mood pills + custom vibe input + results (current Moods page content)
- Advanced mode: multi-filter form + results (current AdvancedSearch page content)
- All three modes share the same results grid component
- Default mode: Title (what users expect from "Search")

---

### 4. Explore (`/explore`)
**Merges 4 people/tag browsing pages into one with tabs.**

| Tab | Old Page | Route |
|-----|----------|-------|
| Directors | Directors | `/explore/directors` |
| Actors | Actors | `/explore/actors` |
| Cast Combo | CastCombo | `/explore/cast-combo` |
| Keywords | Keywords | `/explore/keywords` |

**Implementation:**
- Shared layout with tab bar
- Each tab renders the existing page's inner content
- Directors/Actors tabs share similar UI patterns (search + filmography view)
- Cast Combo has its multi-select actor picker
- Keywords has its tag cloud/search pattern

---

### 5. For You (`/for-you`)
**Merges 3 recommendation pages into one with tabs.**

| Tab | Old Page | Route |
|-----|----------|-------|
| Recommendations | Recommendations | `/for-you` or `/for-you/recommendations` |
| Blind Spots | BlindSpots | `/for-you/blind-spots` |
| Rewatch | Rewatch | `/for-you/rewatch` |

**Implementation:**
- Shared layout with tab bar
- Recommendations tab: keeps strategy selector, diversity slider, topK control, explanation modal
- Blind Spots tab: genre filter + popular unwatched movies
- Rewatch tab: high-rated old movies to revisit
- All tabs are "movies the system thinks you should watch" — they belong together

---

### 6. Library (`/library`)
**Merges 5 list/collection pages into one with tabs.**

| Tab | Old Page | Route |
|-----|----------|-------|
| Watchlist | Watchlist | `/library` or `/library/watchlist` |
| My Lists | Lists | `/library/lists` |
| Collections | Collections | `/library/collections` |
| Gaps | DirectorGaps | `/library/gaps` |
| Curated | Curated | `/library/curated` |

**Implementation:**
- Shared layout with tab bar
- Watchlist tab: user's saved-for-later movies with remove buttons, link to watchlist recommendations
- My Lists tab: user-created custom lists with CRUD
- Collections tab: "Complete the Collection" — finish started director/actor collections
- Gaps tab: missing films from favorite directors/actors
- Curated tab: auto-generated thematic collections (genre/decade, director, year)
- Sub-routes like `/library/lists/:id` for list detail still work

---

### 7. Activity (`/activity`)
**Merges 4 gamification/tracking pages into one with tabs.**

| Tab | Old Page | Route |
|-----|----------|-------|
| Achievements | Achievements | `/activity` or `/activity/achievements` |
| Challenges | Challenges | `/activity/challenges` |
| Bingo | Bingo | `/activity/bingo` |
| Diary | Diary | `/activity/diary` |

**Implementation:**
- Shared layout with tab bar
- Achievements tab: badge grid with unlock status
- Challenges tab: weekly challenge cards with progress bars
- Bingo tab: monthly 5x5 bingo card
- Diary tab: GitHub-style heatmap calendar of rating activity

---

### 8. Profile (`/profile`)
**Merges 3 pages into one with tabs/sections.**

| Tab | Old Page | Route |
|-----|----------|-------|
| Overview | Profile | `/profile` or `/profile/overview` |
| Taste Evolution | TasteEvolution | `/profile/taste-evolution` |
| Platform Stats | PlatformStats | `/profile/platform-stats` |

**Implementation:**
- Overview tab: existing Profile content (ratings, stats, taste profile radar, affinities, streaks, import/export)
- Taste Evolution tab: stacked area chart of genre preferences over time
- Platform Stats tab: global platform statistics and highlights

---

## Navigation Design

### Sidebar (Desktop — left side, same as current but only 8 items)

```
Home           (home icon)
Discover       (explore icon)
Search         (search icon)
Explore        (theater_comedy icon)
For You        (auto_awesome icon)
Library        (bookmark icon)
Activity       (emoji_events icon)
Profile        (person icon)
```

### Top Nav Bar (Horizontal — same 8 items, visible on desktop)

The top nav bar mirrors the sidebar exactly. Both show the same 8 items. On mobile, the bottom nav shows the same 8 items.

### In-Page Tab Bar

Each consolidated page gets a horizontal tab bar immediately below the page header. Design:
- Horizontally scrollable on mobile
- Pill-style or underline-style tabs
- Active tab highlighted with the gold accent (`#FFC107`)
- URL updates on tab switch (`/discover/trending`, `/explore/actors`, etc.)
- Browser back/forward navigates between tabs

---

## Implementation Order

Each phase is a **complete, self-contained unit**. After finishing a phase the app should be fully functional — no broken routes, no missing pages. Test before moving on.

---

### Phase 1: Create shared TabLayout component
**Depends on:** Nothing
**What:** Build the reusable tab bar component that every consolidated page will use.
**Files to create:**
- `frontend/src/components/TabLayout.tsx` — accepts tab definitions `{ label, icon, route }[]`, renders a horizontal pill/underline tab bar + React Router `<Outlet>` for nested routes. Horizontally scrollable on mobile. Active tab highlighted with `#FFC107`.

**Done when:** Component exists, exported, compiles. No visible changes to the app yet.

---

### Phase 2: Consolidate Discover page (merges 7 pages → 1)
**Depends on:** Phase 1
**What:** Merge Discover, Trending, TopCharts, HiddenGems, Seasonal, Controversial, Decades into one tabbed page.
**Steps:**
1. Create `frontend/src/pages/discover/` directory
2. Extract each old page's inner content (strip layout wrapper) into a tab component:
   - `DiscoverLayout.tsx` — TabLayout wrapper defining 7 tabs
   - `BrowseTab.tsx` ← content from `Discover.tsx`
   - `TrendingTab.tsx` ← content from `Trending.tsx`
   - `TopChartsTab.tsx` ← content from `TopCharts.tsx`
   - `HiddenGemsTab.tsx` ← content from `HiddenGems.tsx`
   - `SeasonalTab.tsx` ← content from `Seasonal.tsx`
   - `ControversialTab.tsx` ← content from `Controversial.tsx`
   - `DecadesTab.tsx` ← content from `Decades.tsx`
3. Update `App.tsx` — replace 7 flat routes with nested routes under `/discover`:
   - `/discover` → redirects to `/discover/browse`
   - `/discover/browse`, `/discover/trending`, `/discover/top-charts`, `/discover/hidden-gems`, `/discover/seasonal`, `/discover/controversial`, `/discover/decades`
4. Update `Sidebar.tsx` — remove Trending, Top Charts, Hidden Gems, Seasonal, Controversial, Decades entries (keep only Discover)
5. Update `TopNav.tsx` — remove Trending, Top Charts, Hidden Gems, Decades entries
6. Search entire codebase for links to old routes (`/trending`, `/top-charts`, `/hidden-gems`, `/seasonal`, `/controversial`, `/decades`) and update them to new paths
7. Delete old standalone files: `Trending.tsx`, `TopCharts.tsx`, `HiddenGems.tsx`, `Seasonal.tsx`, `Controversial.tsx`, `Decades.tsx`, old `Discover.tsx`

**Done when:** `/discover/trending` works, `/trending` no longer exists (or redirects), sidebar shows "Discover" instead of 7 separate items.

---

### Phase 3: Consolidate Search page (merges 3 pages → 1)
**Depends on:** Phase 1
**What:** Merge Search, Moods, AdvancedSearch into one page with a mode toggle.
**Steps:**
1. Create `frontend/src/pages/search/` directory
2. Extract each page's inner content into a tab component:
   - `SearchLayout.tsx` — TabLayout wrapper with 3 tabs (Title / Vibe & Mood / Advanced)
   - `TitleSearchTab.tsx` ← content from `Search.tsx`
   - `MoodSearchTab.tsx` ← content from `Moods.tsx`
   - `AdvancedSearchTab.tsx` ← content from `AdvancedSearch.tsx`
3. Update `App.tsx` — replace 3 flat routes with nested routes under `/search`:
   - `/search` → redirects to `/search/title`
   - `/search/title`, `/search/mood`, `/search/advanced`
4. Update `Sidebar.tsx` — remove Moods and Advanced entries, replace with single "Search" entry
5. Update `TopNav.tsx` — same
6. Search codebase for links to `/moods`, `/advanced-search` and update to `/search/mood`, `/search/advanced`
7. Delete old files: `Search.tsx`, `Moods.tsx`, `AdvancedSearch.tsx`

**Done when:** `/search/mood` works, `/moods` no longer exists, sidebar shows "Search" instead of 3 items.

---

### Phase 4: Consolidate Explore page (merges 4 pages → 1)
**Depends on:** Phase 1
**What:** Merge Directors, Actors, CastCombo, Keywords into one tabbed page.
**Steps:**
1. Create `frontend/src/pages/explore/` directory
2. Extract each page's inner content:
   - `ExploreLayout.tsx` — TabLayout wrapper with 4 tabs
   - `DirectorsTab.tsx` ← content from `Directors.tsx`
   - `ActorsTab.tsx` ← content from `Actors.tsx`
   - `CastComboTab.tsx` ← content from `CastCombo.tsx`
   - `KeywordsTab.tsx` ← content from `Keywords.tsx`
3. Update `App.tsx` — nested routes under `/explore`:
   - `/explore` → redirects to `/explore/directors`
   - `/explore/directors`, `/explore/actors`, `/explore/cast-combo`, `/explore/keywords`
4. Update `Sidebar.tsx` — remove Directors, Actors, Cast Combo, Keywords; add single "Explore" entry
5. Update `TopNav.tsx` — remove Directors, Actors entries; add "Explore"
6. Search codebase for links to `/directors`, `/actors`, `/cast-combo`, `/keywords` and update
7. Delete old files: `Directors.tsx`, `Actors.tsx`, `CastCombo.tsx`, `Keywords.tsx`

**Done when:** `/explore/actors` works, `/actors` no longer exists, sidebar shows "Explore" instead of 4 items.

---

### Phase 5: Consolidate For You page (merges 3 pages → 1)
**Depends on:** Phase 1
**What:** Merge Recommendations, BlindSpots, Rewatch into one tabbed page.
**Steps:**
1. Create `frontend/src/pages/for-you/` directory
2. Extract each page's inner content:
   - `ForYouLayout.tsx` — TabLayout wrapper with 3 tabs
   - `RecommendationsTab.tsx` ← content from `Recommendations.tsx`
   - `BlindSpotsTab.tsx` ← content from `BlindSpots.tsx`
   - `RewatchTab.tsx` ← content from `Rewatch.tsx`
3. Update `App.tsx` — nested routes under `/for-you`:
   - `/for-you` → redirects to `/for-you/recommendations`
   - `/for-you/recommendations`, `/for-you/blind-spots`, `/for-you/rewatch`
   - Keep `/recommendations/from-seed/:movieId` as a standalone route (it's a sub-page, not a tab)
4. Update `Sidebar.tsx` — remove Recommendations, Blind Spots entries; add "For You"
5. Update `TopNav.tsx` — remove Recommendations; add "For You"
6. Search codebase for links to `/recommendations`, `/blind-spots`, `/rewatch` and update
7. Delete old files: `Recommendations.tsx`, `BlindSpots.tsx`, `Rewatch.tsx`

**Done when:** `/for-you/recommendations` works with strategy selector and explanation modals, `/recommendations` no longer exists, sidebar shows "For You".

---

### Phase 6: Consolidate Library page (merges 5 pages → 1)
**Depends on:** Phase 1
**What:** Merge Watchlist, Lists, Collections, DirectorGaps, Curated into one tabbed page.
**Steps:**
1. Create `frontend/src/pages/library/` directory
2. Extract each page's inner content:
   - `LibraryLayout.tsx` — TabLayout wrapper with 5 tabs
   - `WatchlistTab.tsx` ← content from `Watchlist.tsx`
   - `ListsTab.tsx` ← content from `Lists.tsx`
   - `CollectionsTab.tsx` ← content from `Collections.tsx`
   - `GapsTab.tsx` ← content from `DirectorGaps.tsx`
   - `CuratedTab.tsx` ← content from `Curated.tsx`
3. Update `App.tsx` — nested routes under `/library`:
   - `/library` → redirects to `/library/watchlist`
   - `/library/watchlist`, `/library/lists`, `/library/collections`, `/library/gaps`, `/library/curated`
   - Keep sub-routes: `/library/lists/:id` for ListDetail, `/library/lists/popular` for PopularLists
   - Keep `/watchlist/recommendations` as standalone (or move to `/library/watchlist/recommendations`)
4. Update `Sidebar.tsx` — remove Watchlist, My Lists, Collections, Director Gaps, Curated; add "Library"
5. Update `TopNav.tsx` — remove Watchlist; add "Library"
6. Search codebase for links to `/watchlist`, `/lists`, `/collections`, `/director-gaps`, `/curated` and update
7. Delete old files: `Watchlist.tsx`, `Lists.tsx`, `Collections.tsx`, `DirectorGaps.tsx`, `Curated.tsx`

**Done when:** `/library/watchlist` works, `/watchlist` no longer exists, sidebar shows "Library" instead of 5 items.

---

### Phase 7: Consolidate Activity page (merges 4 pages → 1)
**Depends on:** Phase 1
**What:** Merge Achievements, Challenges, Bingo, Diary into one tabbed page.
**Steps:**
1. Create `frontend/src/pages/activity/` directory
2. Extract each page's inner content:
   - `ActivityLayout.tsx` — TabLayout wrapper with 4 tabs
   - `AchievementsTab.tsx` ← content from `Achievements.tsx`
   - `ChallengesTab.tsx` ← content from `Challenges.tsx`
   - `BingoTab.tsx` ← content from `Bingo.tsx`
   - `DiaryTab.tsx` ← content from `Diary.tsx`
3. Update `App.tsx` — nested routes under `/activity`:
   - `/activity` → redirects to `/activity/achievements`
   - `/activity/achievements`, `/activity/challenges`, `/activity/bingo`, `/activity/diary`
4. Update `Sidebar.tsx` — remove Challenges, Achievements, Movie Bingo entries; add "Activity"
5. Update `TopNav.tsx` — same
6. Search codebase for links to `/achievements`, `/challenges`, `/bingo`, `/diary` and update
7. Delete old files: `Achievements.tsx`, `Challenges.tsx`, `Bingo.tsx`, `Diary.tsx`

**Done when:** `/activity/bingo` works, `/bingo` no longer exists, sidebar shows "Activity" instead of 4 items.

---

### Phase 8: Consolidate Profile page (merges 3 pages → 1)
**Depends on:** Phase 1
**What:** Merge Profile, TasteEvolution, PlatformStats into one tabbed page.
**Steps:**
1. Create `frontend/src/pages/profile/` directory
2. Extract each page's inner content:
   - `ProfileLayout.tsx` — TabLayout wrapper with 3 tabs
   - `OverviewTab.tsx` ← content from `Profile.tsx`
   - `TasteEvolutionTab.tsx` ← content from `TasteEvolution.tsx`
   - `PlatformStatsTab.tsx` ← content from `PlatformStats.tsx`
3. Update `App.tsx` — nested routes under `/profile`:
   - `/profile` → redirects to `/profile/overview`
   - `/profile/overview`, `/profile/taste-evolution`, `/profile/platform-stats`
4. Update `Sidebar.tsx` — remove Taste Evolution, Platform Stats entries (Profile already exists)
5. Update `TopNav.tsx` — same
6. Search codebase for links to `/taste-evolution`, `/platform-stats` and update
7. Delete old files: `Profile.tsx`, `TasteEvolution.tsx`, `PlatformStats.tsx`

**Done when:** `/profile/taste-evolution` works, `/taste-evolution` no longer exists, sidebar shows only "Profile".

---

### Phase 9: Final navigation update
**Depends on:** Phases 2–8
**What:** Ensure Sidebar, TopNav, and BottomNav all show exactly the same 8 items.
**Steps:**
1. Final `Sidebar.tsx` should have exactly these 8 items:
   ```
   Home           (home)            → /
   Discover       (explore)         → /discover
   Search         (search)          → /search
   Explore        (theater_comedy)  → /explore
   For You        (auto_awesome)    → /for-you
   Library        (bookmark)        → /library
   Activity       (emoji_events)    → /activity
   Profile        (person)          → /profile
   ```
2. `TopNav.tsx` — same 8 items in horizontal layout
3. `BottomNav.tsx` — same 8 items (or top 5 + "more" menu on mobile)
4. Verify active state highlighting works with nested routes (e.g., `/discover/trending` highlights "Discover", `/library/lists/42` highlights "Library")

**Done when:** All three nav components show exactly 8 items, active states work on all nested routes.

---

### Phase 10: Cleanup and redirects
**Depends on:** Phase 9
**What:** Final sweep for broken links, add redirects, verify zero feature loss.
**Steps:**
1. Add redirect routes in `App.tsx` from all old paths to new paths for bookmarks:
   - `/trending` → `/discover/trending`
   - `/top-charts` → `/discover/top-charts`
   - `/hidden-gems` → `/discover/hidden-gems`
   - `/seasonal` → `/discover/seasonal`
   - `/controversial` → `/discover/controversial`
   - `/decades` → `/discover/decades`
   - `/moods` → `/search/mood`
   - `/advanced-search` → `/search/advanced`
   - `/directors` → `/explore/directors`
   - `/actors` → `/explore/actors`
   - `/cast-combo` → `/explore/cast-combo`
   - `/keywords` → `/explore/keywords`
   - `/recommendations` → `/for-you/recommendations`
   - `/blind-spots` → `/for-you/blind-spots`
   - `/rewatch` → `/for-you/rewatch`
   - `/watchlist` → `/library/watchlist`
   - `/lists` → `/library/lists`
   - `/collections` → `/library/collections`
   - `/director-gaps` → `/library/gaps`
   - `/curated` → `/library/curated`
   - `/achievements` → `/activity/achievements`
   - `/challenges` → `/activity/challenges`
   - `/bingo` → `/activity/bingo`
   - `/diary` → `/activity/diary`
   - `/taste-evolution` → `/profile/taste-evolution`
   - `/platform-stats` → `/profile/platform-stats`
2. Grep entire codebase for any remaining references to old routes
3. Verify all old standalone page files are deleted (none left in `frontend/src/pages/` root except `Home.tsx`, `MovieDetail.tsx`, `Onboarding.tsx`, `Compare.tsx`, `FromSeedRecommendations.tsx`, `WatchlistRecommendations.tsx`)
4. Test every tab in every consolidated page
5. Test browser back/forward across tab switches
6. Test deep-linking (paste `/discover/hidden-gems` in new tab)
7. Verify no features were lost against the feature mapping table above

---

## Before vs. After

### Sidebar Before (30 items):
```
Home, Discover, Trending, Top Charts, Hidden Gems, Seasonal,
Controversial, Moods, Decades, Directors, Actors, Cast Combo,
Keywords, Collections, Director Gaps, Curated, Advanced,
Recommendations, Blind Spots, Watchlist, My Lists, Taste Evolution,
Challenges, Achievements, Movie Bingo, Platform Stats, Profile
```

### Sidebar After (8 items):
```
Home, Discover, Search, Explore, For You, Library, Activity, Profile
```

### Feature Mapping (zero features lost):

| Feature | Old Location | New Location |
|---------|-------------|--------------|
| Personalized Home Feed | Home | Home (unchanged) |
| Browse with filters | Discover | Discover → Browse tab |
| Trending movies | Trending | Discover → Trending tab |
| Top charts by genre | Top Charts | Discover → Top Charts tab |
| Hidden gems | Hidden Gems | Discover → Hidden Gems tab |
| Seasonal picks | Seasonal | Discover → Seasonal tab |
| Controversial/divisive | Controversial | Discover → Controversial tab |
| Decade browsing | Decades | Discover → Decades tab |
| Title search | Search | Search → Title mode |
| Mood/vibe search | Moods | Search → Vibe & Mood mode |
| Advanced multi-filter | Advanced Search | Search → Advanced mode |
| Director filmography | Directors | Explore → Directors tab |
| Actor filmography | Actors | Explore → Actors tab |
| Cast combination search | Cast Combo | Explore → Cast Combo tab |
| Keyword/tag browsing | Keywords | Explore → Keywords tab |
| Personalized recs | Recommendations | For You → Recommendations tab |
| Blind spots | Blind Spots | For You → Blind Spots tab |
| Rewatch suggestions | Rewatch | For You → Rewatch tab |
| Watchlist | Watchlist | Library → Watchlist tab |
| Custom lists | My Lists | Library → My Lists tab |
| Complete collections | Collections | Library → Collections tab |
| Director/actor gaps | Director Gaps | Library → Gaps tab |
| Curated collections | Curated | Library → Curated tab |
| Achievement badges | Achievements | Activity → Achievements tab |
| Weekly challenges | Challenges | Activity → Challenges tab |
| Movie bingo | Bingo | Activity → Bingo tab |
| Rating diary/heatmap | Diary | Activity → Diary tab |
| Profile & stats | Profile | Profile → Overview tab |
| Taste evolution | Taste Evolution | Profile → Taste Evolution tab |
| Platform stats | Platform Stats | Profile → Platform Stats tab |
| Movie comparison | Compare | Standalone route (no sidebar entry) |
| Seed-based recs | FromSeedRecs | Standalone route (no sidebar entry) |
| Watchlist-based recs | WatchlistRecs | Standalone route (no sidebar entry) |
| List detail | ListDetail | Nested under Library |
| Popular lists | PopularLists | Nested under Library |
| Onboarding | Onboarding | Standalone route (no sidebar entry) |
| Movie detail | MovieDetail | Standalone route (no sidebar entry) |
