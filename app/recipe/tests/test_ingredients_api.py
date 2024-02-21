"""
Tests for Ingredients API.
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from recipe.serializers import IngredientSerializer

from core.models import (
    Ingredient,
    Recipe,
)

INGREDIENTS_URL = reverse('recipe:ingredient-list')


def detail_url(ingredient_id):
    """Create and return an ingredient detail URL."""
    return reverse('recipe:ingredient-detail', args=[ingredient_id])


def create_user(email='user@example.com', password='password1234'):
    """Create and return user."""
    return get_user_model().objects.create_user(email=email, password=password)


class PublicIngredientsApiTest(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required for retreiving ingredients."""
        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientsApiTest(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def test_retreive_ingredients(self):
        """Test retreiving a list of ingredients."""
        Ingredient.objects.create(user=self.user, name="Ingredient 1")
        Ingredient.objects.create(user=self.user, name="Ingredient 2")

        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)
        self.assertEqual(res.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        """Test list of ingredients is limited to authenticated user."""
        other_user = create_user(email='other@example.com')
        ingredient1 = Ingredient.objects.create(
            user=self.user,
            name='Ingredient user1'
        )
        ingredient2 = Ingredient.objects.create(
            user=other_user,
            name='Ingredient user2',
        )

        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

        ingredients = Ingredient.objects.filter(user=other_user)
        self.assertEqual(ingredients.count(), 1)
        self.assertEqual(ingredients[0].name, ingredient2.name)
        self.assertEqual(res.data[0]['name'], ingredient1.name)

    def test_update_ingredient(self):
        """Test update ingredient is successful."""
        ingredient = Ingredient.objects.create(
            user=self.user,
            name='Ingredient 1')

        payload = {'name': 'Updated name 1'}

        url = detail_url(ingredient.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, payload['name'])

    def test_delete_ingredient(self):
        """Test Deleting an ingredient."""
        Ingredient.objects.create(user=self.user, name='Ingredient0')
        ingredient = Ingredient.objects.create(
            user=self.user,
            name='Ingredient1')

        url = detail_url(ingredient.id)
        res = self.client.delete(url)

        ingredients = Ingredient.objects.filter(user=self.user)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(ingredients.count(), 1)
        self.assertNotIn(ingredient, ingredients)
        # self.assertFalse(ingredient.exists())

    def test_filter_ingredients_assigned_to_recipes(self):
        """Test listing ingredients to those assigned to recipes."""
        in1 = Ingredient.objects.create(user=self.user, name='Apples')
        in2 = Ingredient.objects.create(user=self.user, name='Turkey')
        recipe = Recipe.objects.create(
            user=self.user,
            title='sample recipe 1',
            time_minutes=15,
            price=Decimal('12.2')
        )
        recipe.ingredients.add(in1)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        s1 = IngredientSerializer(in1)
        s2 = IngredientSerializer(in2)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_ingredient_unique(self):
        """Test filtered ingredients a unique list."""
        ing = Ingredient.objects.create(user=self.user, name='Eggs')
        Ingredient.objects.create(user=self.user, name='Lentils')

        recipe1 = Recipe.objects.create(
            user=self.user,
            title='Eggs Benedict',
            time_minutes=45,
            price=Decimal('50.0'),)
        recipe2 = Recipe.objects.create(
            title='Royal Benedict',
            price=Decimal('55.0'),
            time_minutes=55,
            user=self.user,
        )

        recipe1.ingredients.add(ing)
        recipe2.ingredients.add(ing)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)
