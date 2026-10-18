"""
Tests for reading meal plans from Mealie's paginated date-range endpoint.

GET /api/households/mealplans returns a pagination envelope
({page, perPage, total, items}), not a bare list. These tests use that real
shape, which the older mocks did not.
"""

import json
from datetime import date
from unittest.mock import MagicMock, patch

from src.client import mealplan_entries, mealplan_range_params
from src.resources.mealplans import get_current_mealplan
from src.tools.mealplans import (
    mealplans_delete_range,
    mealplans_get_by_date,
    mealplans_list,
    mealplans_search,
)
from src.tools.shopping import shopping_generate_from_mealplan


TODAY = date.today().isoformat()

DINNER = {
    "id": 11, "date": TODAY, "entryType": "dinner", "title": "", "text": "",
    "recipeId": "recipe-1",
    "recipe": {"id": "recipe-1", "name": "Pasta al pomodoro", "slug": "pasta-al-pomodoro"},
}
LUNCH_NOTE = {
    "id": 12, "date": TODAY, "entryType": "lunch", "title": "Leftovers", "text": "use the soup",
    "recipeId": None, "recipe": None,
}


def envelope(*items):
    return {"page": 1, "perPage": -1, "total": len(items), "totalPages": 1, "items": list(items)}


def mock_client(get_value):
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=None)
    mock.get.return_value = get_value
    return mock


class TestHelpers:

    def test_range_params_ask_for_every_page(self):
        assert mealplan_range_params("2026-10-01", "2026-10-07") == {
            "page": 1, "perPage": -1, "start_date": "2026-10-01", "end_date": "2026-10-07",
        }
        assert mealplan_range_params(None, None) == {"page": 1, "perPage": -1}

    def test_entries_unwrap_the_envelope(self):
        assert mealplan_entries(envelope(DINNER, LUNCH_NOTE)) == [DINNER, LUNCH_NOTE]

    def test_entries_accept_a_bare_list_and_ignore_junk(self):
        assert mealplan_entries([DINNER, "x", None]) == [DINNER]
        assert mealplan_entries(envelope()) == []
        assert mealplan_entries({"items": None}) == []
        assert mealplan_entries(None) == []


class TestGetByDate:

    def test_fields_come_from_the_entries_not_the_envelope(self):
        mock = mock_client(envelope(DINNER, LUNCH_NOTE))
        with patch("src.tools.mealplans.MealieClient", return_value=mock):
            data = json.loads(mealplans_get_by_date(TODAY))

        assert data["count"] == 2
        assert data["meals"]["dinner"] == [{
            "id": 11, "title": "", "text": "", "recipe_id": "recipe-1",
            "recipe_name": "Pasta al pomodoro", "recipe_slug": "pasta-al-pomodoro",
        }]
        assert data["meals"]["lunch"][0]["title"] == "Leftovers"
        assert data["meals"]["lunch"][0]["recipe_id"] is None
        assert mock.get.call_args.kwargs["params"]["perPage"] == -1

    def test_empty_day_counts_zero(self):
        """An empty envelope used to be counted as one null meal."""
        mock = mock_client(envelope())
        with patch("src.tools.mealplans.MealieClient", return_value=mock):
            data = json.loads(mealplans_get_by_date(TODAY))

        assert data == {"date": TODAY, "count": 0, "meals": {}}


class TestList:

    def test_envelope_is_formatted(self):
        mock = mock_client(envelope(DINNER))
        with patch("src.tools.mealplans.MealieClient", return_value=mock):
            data = json.loads(mealplans_list(start_date=TODAY, end_date=TODAY))

        assert data["count"] == 1
        assert data["entries"][0]["entry_type"] == "dinner"
        assert data["entries"][0]["recipe_name"] == "Pasta al pomodoro"
        assert mock.get.call_args.kwargs["params"] == mealplan_range_params(TODAY, TODAY)


class TestSearchAndDeleteRange:

    def test_search_reads_the_entries(self):
        mock = mock_client(envelope(DINNER, LUNCH_NOTE))
        with patch("src.tools.mealplans.MealieClient", return_value=mock):
            data = json.loads(mealplans_search("pomodoro", start_date=TODAY, end_date=TODAY))

        assert data["success"] is True
        assert [plan["id"] for plan in data["meal_plans"]] == [11]

    def test_delete_range_deletes_each_entry(self):
        mock = mock_client(envelope(DINNER, LUNCH_NOTE))
        with patch("src.tools.mealplans.MealieClient", return_value=mock):
            json.loads(mealplans_delete_range(start_date=TODAY, end_date=TODAY))

        deleted = [call.args[0] for call in mock.delete.call_args_list]
        assert deleted == ["/api/households/mealplans/11", "/api/households/mealplans/12"]


class TestOtherReaders:

    def test_current_week_resource_lists_the_meals(self):
        mock = mock_client(envelope(DINNER))
        with patch("src.resources.mealplans.MealieClient", return_value=mock):
            text = get_current_mealplan()

        assert "Pasta al pomodoro" in text

    def test_shopping_from_mealplan_finds_the_recipes(self):
        mock = mock_client(envelope(DINNER, LUNCH_NOTE))
        mock.post.return_value = {"id": "list-1", "name": "Meal plan"}
        with patch("src.tools.shopping.MealieClient", return_value=mock):
            data = json.loads(shopping_generate_from_mealplan(start_date=TODAY, end_date=TODAY))

        assert "No meal plans found" not in data.get("error", "")
        assert "No recipes found" not in data.get("error", "")
