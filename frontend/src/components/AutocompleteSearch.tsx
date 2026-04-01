import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { autocompleteMovies } from "../api/movies";
import type { AutocompleteSuggestion } from "../api/types";

const TMDB_IMG = "https://image.tmdb.org/t/p/w92";

interface AutocompleteSearchProps {
  placeholder?: string;
  className?: string;
  inputClassName?: string;
  onNavigateToSearch?: (query: string) => void;
}

export default function AutocompleteSearch({
  placeholder = "Search for titles, directors, or genres...",
  className = "",
  inputClassName = "",
  onNavigateToSearch,
}: AutocompleteSearchProps) {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<AutocompleteSuggestion[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [loading, setLoading] = useState(false);

  const debounceRef = useRef<ReturnType<typeof setTimeout>>();
  const abortRef = useRef<AbortController>();
  const wrapperRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  const totalItems = results.length + 1; // +1 for "See all results"

  const fetchSuggestions = useCallback((q: string) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (abortRef.current) abortRef.current.abort();

    if (!q.trim()) {
      setResults([]);
      setIsOpen(false);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      const controller = new AbortController();
      abortRef.current = controller;
      setLoading(true);
      try {
        const data = await autocompleteMovies(q.trim(), 8, controller.signal);
        setResults(data.results);
        setIsOpen(data.results.length > 0);
        setActiveIndex(-1);
      } catch {
        // aborted or network error — ignore
      } finally {
        setLoading(false);
      }
    }, 300);
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);
    fetchSuggestions(value);
  };

  const selectMovie = (id: number) => {
    setIsOpen(false);
    navigate(`/movies/${id}`);
  };

  const goToFullSearch = () => {
    if (!query.trim()) return;
    setIsOpen(false);
    if (onNavigateToSearch) {
      onNavigateToSearch(query.trim());
    } else {
      navigate(`/discover?q=${encodeURIComponent(query.trim())}`);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) {
      if (e.key === "Enter") {
        e.preventDefault();
        goToFullSearch();
      }
      return;
    }

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setActiveIndex((prev) => (prev + 1) % totalItems);
        break;
      case "ArrowUp":
        e.preventDefault();
        setActiveIndex((prev) => (prev - 1 + totalItems) % totalItems);
        break;
      case "Enter":
        e.preventDefault();
        if (activeIndex >= 0 && activeIndex < results.length) {
          selectMovie(results[activeIndex].id);
        } else {
          goToFullSearch();
        }
        break;
      case "Escape":
        setIsOpen(false);
        setActiveIndex(-1);
        break;
    }
  };

  // Scroll active item into view
  useEffect(() => {
    if (activeIndex >= 0 && listRef.current) {
      const item = listRef.current.children[activeIndex] as HTMLElement;
      item?.scrollIntoView({ block: "nearest" });
    }
  }, [activeIndex]);

  // Click outside to close
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      if (abortRef.current) abortRef.current.abort();
    };
  }, []);

  return (
    <div ref={wrapperRef} className={`relative ${className}`}>
      <div className="relative">
        <div className="absolute inset-y-0 left-6 flex items-center pointer-events-none">
          <span className="material-symbols-outlined text-outline">search</span>
        </div>
        <input
          value={query}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onFocus={() => results.length > 0 && setIsOpen(true)}
          className={inputClassName}
          placeholder={placeholder}
          type="text"
          role="combobox"
          aria-expanded={isOpen}
          aria-autocomplete="list"
          aria-controls="autocomplete-listbox"
          autoComplete="off"
        />
        {loading && (
          <div className="absolute inset-y-0 right-6 flex items-center pointer-events-none">
            <div className="w-4 h-4 border-2 border-outline/40 border-t-primary rounded-full animate-spin" />
          </div>
        )}
      </div>

      {isOpen && (
        <ul
          ref={listRef}
          id="autocomplete-listbox"
          role="listbox"
          className="absolute z-50 w-full mt-2 bg-surface-container/95 backdrop-blur-xl rounded-xl shadow-2xl border border-outline/10 overflow-hidden"
        >
          {results.map((item, i) => (
            <li
              key={item.id}
              role="option"
              aria-selected={i === activeIndex}
              className={`flex items-center gap-3 px-4 py-2.5 cursor-pointer transition-colors ${
                i === activeIndex
                  ? "bg-surface-container-highest"
                  : "hover:bg-surface-container-high"
              }`}
              onMouseEnter={() => setActiveIndex(i)}
              onMouseDown={(e) => {
                e.preventDefault();
                selectMovie(item.id);
              }}
            >
              {item.poster_path ? (
                <img
                  src={`${TMDB_IMG}${item.poster_path}`}
                  alt=""
                  className="w-8 h-12 rounded object-cover flex-shrink-0"
                />
              ) : (
                <div className="w-8 h-12 rounded bg-surface-container-highest flex items-center justify-center flex-shrink-0">
                  <span className="material-symbols-outlined text-outline text-sm">movie</span>
                </div>
              )}
              <div className="min-w-0">
                <p className="text-on-surface text-sm font-medium truncate">{item.title}</p>
                {item.year && (
                  <p className="text-on-surface-variant text-xs">{item.year}</p>
                )}
              </div>
            </li>
          ))}
          <li
            role="option"
            aria-selected={activeIndex === results.length}
            className={`px-4 py-3 cursor-pointer text-center text-sm transition-colors border-t border-outline/10 ${
              activeIndex === results.length
                ? "bg-surface-container-highest text-primary"
                : "text-on-surface-variant hover:bg-surface-container-high hover:text-primary"
            }`}
            onMouseEnter={() => setActiveIndex(results.length)}
            onMouseDown={(e) => {
              e.preventDefault();
              goToFullSearch();
            }}
          >
            See all results for "<span className="font-medium text-on-surface">{query}</span>"
          </li>
        </ul>
      )}
    </div>
  );
}
