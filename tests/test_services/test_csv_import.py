"""Tests for CSV import parsing utilities."""

from __future__ import annotations

import csv
import io

import pytest

from cinematch.services.csv_import import (
    detect_source,
    parse_csv_content,
    parse_imdb_csv,
    parse_letterboxd_csv,
)


class TestDetectSource:
    def test_imdb_headers(self):
        headers = ["Const", "Your Rating", "Date Rated", "Title", "URL"]
        assert detect_source(headers) == "imdb"

    def test_letterboxd_headers(self):
        headers = ["Date", "Name", "Year", "Letterboxd URI", "Rating"]
        assert detect_source(headers) == "letterboxd"

    def test_unknown_headers_raises(self):
        with pytest.raises(ValueError, match="Unrecognized CSV format"):
            detect_source(["col1", "col2", "col3"])


class TestParseLetterboxdCsv:
    def _make_reader(self, rows: list[dict]) -> csv.DictReader:
        output = io.StringIO()
        writer = csv.DictWriter(
            output, fieldnames=["Date", "Name", "Year", "Letterboxd URI", "Rating"]
        )
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
        output.seek(0)
        return csv.DictReader(output)

    def test_scaling_half_star(self):
        reader = self._make_reader(
            [
                {
                    "Date": "2024-01-01",
                    "Name": "Movie A",
                    "Year": "2020",
                    "Letterboxd URI": "https://...",
                    "Rating": "0.5",
                },
            ]
        )
        result = parse_letterboxd_csv(reader)
        assert len(result) == 1
        assert result[0]["scaled_rating"] == 1

    def test_scaling_mid(self):
        reader = self._make_reader(
            [
                {
                    "Date": "2024-01-01",
                    "Name": "Movie B",
                    "Year": "2020",
                    "Letterboxd URI": "https://...",
                    "Rating": "2.5",
                },
            ]
        )
        result = parse_letterboxd_csv(reader)
        assert result[0]["scaled_rating"] == 5

    def test_scaling_max(self):
        reader = self._make_reader(
            [
                {
                    "Date": "2024-01-01",
                    "Name": "Movie C",
                    "Year": "2020",
                    "Letterboxd URI": "https://...",
                    "Rating": "5.0",
                },
            ]
        )
        result = parse_letterboxd_csv(reader)
        assert result[0]["scaled_rating"] == 10

    def test_scaling_three_point_five(self):
        reader = self._make_reader(
            [
                {
                    "Date": "2024-01-01",
                    "Name": "Movie D",
                    "Year": "2020",
                    "Letterboxd URI": "https://...",
                    "Rating": "3.5",
                },
            ]
        )
        result = parse_letterboxd_csv(reader)
        assert result[0]["scaled_rating"] == 7

    def test_skips_empty_rating(self):
        reader = self._make_reader(
            [
                {
                    "Date": "2024-01-01",
                    "Name": "No Rating",
                    "Year": "2020",
                    "Letterboxd URI": "https://...",
                    "Rating": "",
                },
            ]
        )
        result = parse_letterboxd_csv(reader)
        assert len(result) == 0

    def test_preserves_title_and_year(self):
        reader = self._make_reader(
            [
                {
                    "Date": "2024-01-01",
                    "Name": "Inception",
                    "Year": "2010",
                    "Letterboxd URI": "https://...",
                    "Rating": "4.5",
                },
            ]
        )
        result = parse_letterboxd_csv(reader)
        assert result[0]["title"] == "Inception"
        assert result[0]["year"] == 2010
        assert result[0]["original_rating"] == 4.5


class TestParseImdbCsv:
    def _make_reader(self, rows: list[dict]) -> csv.DictReader:
        output = io.StringIO()
        fields = [
            "Const",
            "Your Rating",
            "Date Rated",
            "Title",
            "URL",
            "Title Type",
            "IMDb Rating",
            "Runtime (mins)",
            "Year",
            "Genres",
            "Num Votes",
            "Release Date",
            "Directors",
        ]
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
        output.seek(0)
        return csv.DictReader(output)

    def test_passthrough_rating(self):
        reader = self._make_reader(
            [
                {
                    "Const": "tt0133093",
                    "Your Rating": "9",
                    "Date Rated": "2024-01-01",
                    "Title": "The Matrix",
                    "URL": "",
                    "Title Type": "Movie",
                    "IMDb Rating": "8.7",
                    "Runtime (mins)": "136",
                    "Year": "1999",
                    "Genres": "Action",
                    "Num Votes": "2000000",
                    "Release Date": "1999-03-31",
                    "Directors": "Lana Wachowski",
                },
            ]
        )
        result = parse_imdb_csv(reader)
        assert len(result) == 1
        assert result[0]["scaled_rating"] == 9
        assert result[0]["original_rating"] == 9

    def test_extracts_imdb_id(self):
        reader = self._make_reader(
            [
                {
                    "Const": "tt0468569",
                    "Your Rating": "10",
                    "Date Rated": "2024-01-01",
                    "Title": "The Dark Knight",
                    "URL": "",
                    "Title Type": "Movie",
                    "IMDb Rating": "9.0",
                    "Runtime (mins)": "152",
                    "Year": "2008",
                    "Genres": "Action",
                    "Num Votes": "2500000",
                    "Release Date": "2008-07-18",
                    "Directors": "Christopher Nolan",
                },
            ]
        )
        result = parse_imdb_csv(reader)
        assert result[0]["imdb_id"] == "tt0468569"

    def test_skips_empty_rating(self):
        reader = self._make_reader(
            [
                {
                    "Const": "tt0133093",
                    "Your Rating": "",
                    "Date Rated": "",
                    "Title": "The Matrix",
                    "URL": "",
                    "Title Type": "Movie",
                    "IMDb Rating": "8.7",
                    "Runtime (mins)": "136",
                    "Year": "1999",
                    "Genres": "Action",
                    "Num Votes": "2000000",
                    "Release Date": "1999-03-31",
                    "Directors": "Lana Wachowski",
                },
            ]
        )
        result = parse_imdb_csv(reader)
        assert len(result) == 0

    def test_skips_missing_const(self):
        reader = self._make_reader(
            [
                {
                    "Const": "",
                    "Your Rating": "8",
                    "Date Rated": "2024-01-01",
                    "Title": "Unknown",
                    "URL": "",
                    "Title Type": "Movie",
                    "IMDb Rating": "7.0",
                    "Runtime (mins)": "120",
                    "Year": "2020",
                    "Genres": "Drama",
                    "Num Votes": "1000",
                    "Release Date": "2020-01-01",
                    "Directors": "Unknown",
                },
            ]
        )
        result = parse_imdb_csv(reader)
        assert len(result) == 0


class TestParseCsvContent:
    def test_auto_detect_imdb(self):
        content = "Const,Your Rating,Date Rated,Title,URL\ntt0133093,9,2024-01-01,The Matrix,\n"
        rows, source = parse_csv_content(content, "auto")
        assert source == "imdb"
        assert len(rows) == 1

    def test_auto_detect_letterboxd(self):
        content = (
            "Date,Name,Year,Letterboxd URI,Rating\n2024-01-01,Inception,2010,https://...,4.5\n"
        )
        rows, source = parse_csv_content(content, "auto")
        assert source == "letterboxd"
        assert len(rows) == 1

    def test_forced_source(self):
        content = (
            "Date,Name,Year,Letterboxd URI,Rating\n2024-01-01,Inception,2010,https://...,4.5\n"
        )
        rows, source = parse_csv_content(content, "letterboxd")
        assert source == "letterboxd"
        assert len(rows) == 1
