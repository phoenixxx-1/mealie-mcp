"""
Tests for ingredient substitutions (recipe ingredient lines and foods).

Covers the substitution normalization and name-resolution helpers, the client
read-modify-write methods for food substitutions, the food tool wrappers, and
the substitutions pass-through in recipes_update_structured_ingredients.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
import respx
from httpx import Response

from src.client import (
    MealieClient,
    food_name_index,
    normalize_substitutions,
    resolve_substitutions,
    substitution_summary,
)
from src.tools.foods import (
    foods_create,
    foods_substitutions_add,
    foods_substitutions_remove,
    foods_update,
)
from src.tools.recipes import recipes_update_structured_ingredients


BASE_URL = "https://test.example.com"

BUTTER = {"id": "food-butter", "name": "butter", "pluralName": None, "aliases": []}
VEGAN_BLOCK = {"id": "food-vegan", "name": "vegan block", "pluralName": None,
               "aliases": [{"name": "plant butter"}]}
TOMATO = {"id": "food-tomato", "name": "chopped tomato", "pluralName": "chopped tomatoes",
          "aliases": []}
ALL_FOODS = [BUTTER, VEGAN_BLOCK, TOMATO]


def create_mock_client():
    """Helper to create a mocked MealieClient usable as a context manager."""
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=None)
    return mock


def saved_sub(food=None, note=None):
    """A substitution as Mealie returns it, with the resolved substitute food."""
    return {
        "substituteFoodId": food["id"] if food else None,
        "substituteFood": {"id": food["id"], "name": food["name"]} if food else None,
        "note": note,
    }


def food_with(subs, base=BUTTER):
    return {**base, "substitutions": subs}


def mock_all_foods():
    return respx.get(f"{BASE_URL}/api/foods", params={"perPage": "-1"}).mock(
        return_value=Response(200, json={"items": ALL_FOODS})
    )


class TestNormalizeSubstitutions:
    """Test the substitution validation helper."""

    def test_none_and_empty_return_empty_list(self):
        assert normalize_substitutions(None) == []
        assert normalize_substitutions([]) == []

    def test_string_is_a_food_name(self):
        assert normalize_substitutions(["  vegan block "]) == [
            {"food_id": None, "food_name": "vegan block", "note": None}
        ]

    def test_snake_and_camel_case_keys(self):
        result = normalize_substitutions([
            {"substitute_food_id": "a", "note": " softened "},
            {"substituteFoodId": "b"},
            {"substitute_food": "passata"},
        ])
        assert result == [
            {"food_id": "a", "food_name": None, "note": "softened"},
            {"food_id": "b", "food_name": None, "note": None},
            {"food_id": None, "food_name": "passata", "note": None},
        ]

    def test_accepts_mealie_read_shape(self):
        """Entries copied from mealie_recipes_get / mealie_foods_get round-trip."""
        result = normalize_substitutions([saved_sub(VEGAN_BLOCK, "dairy-free")])
        assert result == [{"food_id": "food-vegan", "food_name": "vegan block", "note": "dairy-free"}]

    def test_note_only_is_allowed(self):
        assert normalize_substitutions([{"note": "water and a stock cube"}]) == [
            {"food_id": None, "food_name": None, "note": "water and a stock cube"}
        ]

    def test_empty_entry_raises(self):
        with pytest.raises(ValueError, match="a substitute food, a note, or both"):
            normalize_substitutions([{"note": "  "}])
        with pytest.raises(ValueError, match="a substitute food, a note, or both"):
            normalize_substitutions([""])

    def test_bad_types_raise(self):
        with pytest.raises(ValueError, match="must be a food name or a dict"):
            normalize_substitutions([42])
        with pytest.raises(ValueError, match="substitute_food must be"):
            normalize_substitutions([{"substitute_food": 42}])
        with pytest.raises(ValueError, match="note must be a string"):
            normalize_substitutions([{"substitute_food": "x", "note": 3}])


class TestResolveSubstitutions:
    """Test food-name indexing and resolution."""

    def test_index_covers_names_plurals_and_aliases(self):
        index = food_name_index(ALL_FOODS)
        assert index["butter"]["id"] == "food-butter"
        assert index["chopped tomatoes"]["id"] == "food-tomato"
        assert index["plant butter"]["id"] == "food-vegan"

    def test_real_name_beats_another_foods_alias(self):
        foods = [{"id": "a", "name": "x", "aliases": [{"name": "butter"}]}, BUTTER]
        assert food_name_index(foods)["butter"]["id"] == "food-butter"

    def test_resolves_case_insensitively_and_reports_unmatched(self):
        subs = normalize_substitutions(["Chopped Tomatoes", "unicorn", {"note": "or skip it"}])
        payload, unmatched = resolve_substitutions(subs, food_name_index(ALL_FOODS))
        assert payload == [
            {"substituteFoodId": "food-tomato", "note": None},
            {"substituteFoodId": None, "note": "or skip it"},
        ]
        assert unmatched == ["unicorn"]

    def test_id_wins_over_name(self):
        subs = normalize_substitutions([{"substitute_food_id": "given", "substitute_food": "butter"}])
        payload, _ = resolve_substitutions(subs, {})
        assert payload == [{"substituteFoodId": "given", "note": None}]

    def test_summary(self):
        assert substitution_summary(food_with([saved_sub(VEGAN_BLOCK, "dairy-free")])) == [
            {"substitute_food_id": "food-vegan", "substitute_food": "vegan block", "note": "dairy-free"}
        ]
        assert substitution_summary({"substitutions": None}) == []


class TestFoodSubstitutionClient:
    """Test the MealieClient food substitution methods."""

    @respx.mock
    def test_create_food_resolves_names(self):
        all_foods = mock_all_foods()
        post = respx.post(f"{BASE_URL}/api/foods").mock(
            return_value=Response(201, json={"id": "new"})
        )

        MealieClient(BASE_URL, "token").create_food(
            "margarine", substitutions=[{"substitute_food": "Butter", "note": "same amount"}]
        )

        assert all_foods.called
        sent = json.loads(post.calls[0].request.content)
        assert sent["substitutions"] == [{"substituteFoodId": "food-butter", "note": "same amount"}]

    @respx.mock
    def test_ids_skip_the_food_lookup(self):
        all_foods = mock_all_foods()
        post = respx.post(f"{BASE_URL}/api/foods").mock(
            return_value=Response(201, json={"id": "new"})
        )

        MealieClient(BASE_URL, "token").create_food(
            "margarine", substitutions=[{"substitute_food_id": "food-butter"}]
        )

        assert not all_foods.called
        assert json.loads(post.calls[0].request.content)["substitutions"] == [
            {"substituteFoodId": "food-butter", "note": None}
        ]

    @respx.mock
    def test_unknown_name_is_rejected_without_writing(self):
        mock_all_foods()
        post = respx.post(f"{BASE_URL}/api/foods")

        with pytest.raises(ValueError, match="unicorn"):
            MealieClient(BASE_URL, "token").create_food("x", substitutions=["unicorn"])

        assert not post.called

    @respx.mock
    def test_update_food_replaces_and_clears(self):
        respx.get(f"{BASE_URL}/api/foods/food-butter").mock(
            return_value=Response(200, json=food_with([saved_sub(TOMATO)]))
        )
        put = respx.put(f"{BASE_URL}/api/foods/food-butter").mock(
            return_value=Response(200, json=food_with([]))
        )
        client = MealieClient(BASE_URL, "token")

        client.update_food("food-butter", substitutions=[{"substitute_food_id": "food-vegan"}])
        assert json.loads(put.calls[0].request.content)["substitutions"] == [
            {"substituteFoodId": "food-vegan", "note": None}
        ]

        client.update_food("food-butter", substitutions=[])
        assert json.loads(put.calls[1].request.content)["substitutions"] == []

    @respx.mock
    def test_update_food_without_substitutions_leaves_them(self):
        existing = [saved_sub(VEGAN_BLOCK)]
        respx.get(f"{BASE_URL}/api/foods/food-butter").mock(
            return_value=Response(200, json=food_with(existing))
        )
        put = respx.put(f"{BASE_URL}/api/foods/food-butter").mock(
            return_value=Response(200, json=food_with(existing))
        )

        MealieClient(BASE_URL, "token").update_food("food-butter", name="Butter")

        assert json.loads(put.calls[0].request.content)["substitutions"] == existing

    @respx.mock
    def test_invalid_substitutions_are_rejected_before_any_request(self):
        get = respx.get(f"{BASE_URL}/api/foods/food-butter")
        all_foods = mock_all_foods()
        client = MealieClient(BASE_URL, "token")

        with pytest.raises(ValueError):
            client.update_food("food-butter", substitutions=[{}])
        with pytest.raises(ValueError):
            client.add_food_substitutions("food-butter", [42])
        with pytest.raises(ValueError):
            client.remove_food_substitutions("food-butter", [{"note": ""}])

        assert not get.called
        assert not all_foods.called

    @respx.mock
    def test_add_preserves_existing_and_updates_notes(self):
        respx.get(f"{BASE_URL}/api/foods/food-butter").mock(
            return_value=Response(200, json=food_with([
                saved_sub(VEGAN_BLOCK, "old note"), saved_sub(note="or oil"),
            ]))
        )
        put = respx.put(f"{BASE_URL}/api/foods/food-butter").mock(
            return_value=Response(200, json=food_with([]))
        )

        MealieClient(BASE_URL, "token").add_food_substitutions("food-butter", [
            {"substitute_food_id": "food-vegan", "note": "new note"},
            {"note": "OR OIL"},
            {"substitute_food_id": "food-tomato"},
        ])

        assert json.loads(put.calls[0].request.content)["substitutions"] == [
            {"substituteFoodId": "food-vegan", "note": "new note"},
            {"substituteFoodId": None, "note": "or oil"},
            {"substituteFoodId": "food-tomato", "note": None},
        ]

    @respx.mock
    def test_add_same_food_without_note_keeps_existing_note(self):
        respx.get(f"{BASE_URL}/api/foods/food-butter").mock(
            return_value=Response(200, json=food_with([saved_sub(VEGAN_BLOCK, "keep me")]))
        )
        put = respx.put(f"{BASE_URL}/api/foods/food-butter").mock(
            return_value=Response(200, json=food_with([]))
        )

        MealieClient(BASE_URL, "token").add_food_substitutions(
            "food-butter", [{"substitute_food_id": "food-vegan"}]
        )

        assert json.loads(put.calls[0].request.content)["substitutions"] == [
            {"substituteFoodId": "food-vegan", "note": "keep me"}
        ]

    @respx.mock
    def test_remove_by_name_id_and_note(self):
        all_foods = mock_all_foods()
        respx.get(f"{BASE_URL}/api/foods/food-butter").mock(
            return_value=Response(200, json=food_with([
                saved_sub(VEGAN_BLOCK, "note"), saved_sub(TOMATO),
                saved_sub(note="or oil"), saved_sub(note="or lard"),
            ]))
        )
        put = respx.put(f"{BASE_URL}/api/foods/food-butter").mock(
            return_value=Response(200, json=food_with([]))
        )

        MealieClient(BASE_URL, "token").remove_food_substitutions("food-butter", [
            "VEGAN BLOCK", {"substitute_food_id": "food-tomato"}, {"note": "Or Oil"}, "unicorn",
        ])

        # Names are matched against the food's own substitutes, so no library fetch
        assert not all_foods.called
        assert json.loads(put.calls[0].request.content)["substitutions"] == [
            {"substituteFoodId": None, "note": "or lard"}
        ]


class TestFoodSubstitutionTools:
    """Test the food tool wrappers."""

    def test_add_returns_summary(self):
        mock = create_mock_client()
        mock.add_food_substitutions.return_value = food_with([saved_sub(VEGAN_BLOCK)])
        with patch("src.tools.foods.MealieClient", return_value=mock):
            data = json.loads(foods_substitutions_add("food-butter", ["vegan block"]))

        assert data["success"] is True
        assert data["substitutions"] == [
            {"substitute_food_id": "food-vegan", "substitute_food": "vegan block", "note": None}
        ]
        mock.add_food_substitutions.assert_called_once_with("food-butter", ["vegan block"])

    def test_remove_returns_summary(self):
        mock = create_mock_client()
        mock.remove_food_substitutions.return_value = food_with([])
        with patch("src.tools.foods.MealieClient", return_value=mock):
            data = json.loads(foods_substitutions_remove("food-butter", ["vegan block"]))

        assert data["success"] is True
        assert data["substitutions"] == []

    def test_validation_error_is_reported_plainly(self):
        mock = create_mock_client()
        mock.update_food.side_effect = ValueError("No existing food matches substitute food name(s): x")
        with patch("src.tools.foods.MealieClient", return_value=mock):
            data = json.loads(foods_update("food-butter", substitutions=["x"]))

        assert data == {"error": "No existing food matches substitute food name(s): x"}

    def test_create_and_update_pass_substitutions_through(self):
        mock = create_mock_client()
        mock.create_food.return_value = {"id": "new"}
        mock.update_food.return_value = {"id": "food-butter"}
        subs = [{"substitute_food": "vegan block"}]
        with patch("src.tools.foods.MealieClient", return_value=mock):
            foods_create("margarine", substitutions=subs)
            foods_update("food-butter", substitutions=subs)

        mock.create_food.assert_called_once_with("margarine", None, None, None, subs)
        mock.update_food.assert_called_once_with("food-butter", None, None, None, None, subs)


class TestStructuredIngredientSubstitutions:
    """Test substitutions on mealie_recipes_update_structured_ingredients lines."""

    @staticmethod
    def _client(saved_lines=None):
        mock = create_mock_client()
        mock.get_food_name_index.return_value = food_name_index(ALL_FOODS)
        mock.update_recipe_ingredients.return_value = {
            "id": "recipe-1", "slug": "test-recipe", "name": "Test Recipe",
            "recipeIngredient": saved_lines or [],
        }
        return mock

    @staticmethod
    def _sent(mock):
        return mock.update_recipe_ingredients.call_args[0][1]

    def test_substitutions_are_sent_and_echoed(self):
        saved = [
            {"display": "1 cup passata", "substitutions": [saved_sub(TOMATO, "drained")]},
            {"display": "salt", "substitutions": []},
        ]
        mock = self._client(saved)
        parsed = [
            {"ingredient": {
                "quantity": 1, "food": {"id": "food-passata", "name": "passata"},
                "substitutions": [{"substitute_food": "chopped tomatoes", "note": "drained"}],
            }},
            {"ingredient": {"food": {"id": "food-salt", "name": "salt"}}},
        ]
        with patch("src.tools.recipes.MealieClient", return_value=mock):
            data = json.loads(recipes_update_structured_ingredients("test-recipe", parsed))

        sent = self._sent(mock)
        assert sent[0]["substitutions"] == [{"substituteFoodId": "food-tomato", "note": "drained"}]
        assert "substitutions" not in sent[1]
        assert data["saved_substitutions"] == [{
            "line": 0, "display": "1 cup passata",
            "substitutions": [{"substitute_food_id": "food-tomato",
                               "substitute_food": "chopped tomato", "note": "drained"}],
        }]

    def test_substitutions_beside_parser_result(self):
        """Substitutions may sit on the parser wrapper next to 'ingredient'."""
        mock = self._client()
        parsed = [{
            "input": "50g butter",
            "ingredient": {"food": {"id": "food-butter", "name": "butter"}},
            "substitutions": [{"substitute_food_id": "food-vegan"}],
        }]
        with patch("src.tools.recipes.MealieClient", return_value=mock):
            recipes_update_structured_ingredients("test-recipe", parsed)

        assert self._sent(mock)[0]["substitutions"] == [{"substituteFoodId": "food-vegan", "note": None}]
        mock.get_food_name_index.assert_not_called()

    def test_missing_substitute_is_created_by_default(self):
        mock = self._client()
        mock.create_food.return_value = {"id": "food-new", "name": "oat cream"}
        parsed = [{"ingredient": {
            "food": {"id": "food-cream", "name": "cream"}, "substitutions": ["oat cream"],
        }}]
        with patch("src.tools.recipes.MealieClient", return_value=mock):
            data = json.loads(recipes_update_structured_ingredients("test-recipe", parsed))

        mock.create_food.assert_called_once_with("oat cream")
        assert data["created_foods"] == {"oat cream": "food-new"}
        assert self._sent(mock)[0]["substitutions"] == [{"substituteFoodId": "food-new", "note": None}]

    def test_missing_substitute_is_reported_when_flag_off(self):
        mock = self._client()
        parsed = [{"ingredient": {
            "food": {"id": "food-cream", "name": "cream"},
            "substitutions": ["oat cream", "plant butter"],
        }}]
        with patch("src.tools.recipes.MealieClient", return_value=mock):
            data = json.loads(recipes_update_structured_ingredients(
                "test-recipe", parsed, create_missing_foods=False
            ))

        assert data["unmatched_foods"] == []
        assert data["unmatched_substitute_foods"] == ["oat cream"]
        mock.create_food.assert_not_called()
        mock.update_recipe_ingredients.assert_not_called()

    def test_invalid_substitution_fails_before_any_request(self):
        mock = self._client()
        parsed = [{"ingredient": {"food": {"name": "new food"}, "substitutions": [{"note": ""}]}}]
        with patch("src.tools.recipes.MealieClient", return_value=mock):
            data = json.loads(recipes_update_structured_ingredients("test-recipe", parsed))

        assert "a substitute food, a note, or both" in data["error"]
        mock.create_food.assert_not_called()
        mock.update_recipe_ingredients.assert_not_called()

    def test_empty_list_clears_a_line(self):
        mock = self._client()
        parsed = [{"ingredient": {"food": {"id": "food-butter", "name": "butter"}, "substitutions": []}}]
        with patch("src.tools.recipes.MealieClient", return_value=mock):
            recipes_update_structured_ingredients("test-recipe", parsed)

        assert self._sent(mock)[0]["substitutions"] == []
