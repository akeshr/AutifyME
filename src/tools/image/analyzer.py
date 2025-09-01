"""
Image Analysis Tool

This tool takes an image and extracts product information using AI.
In Python, we organize related functions into classes.
"""

import base64
from typing import Optional
from pathlib import Path
from PIL import Image
import requests
from io import BytesIO

from src.core.models.cataloging import ProductFeatures


class ImageAnalyzer:
    """
    A class that handles image analysis
    
    In Python:
    - __init__ is the constructor (runs when you create the object)
    - self refers to the current instance of the class
    - Methods are functions inside a class
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the analyzer with API credentials
        """
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1/chat/completions"
    
    def analyze_image(self, image_path: str) -> ProductFeatures:
        """
        Main function to analyze a product image
        
        Args:
            image_path: Path to the image file
            
        Returns:
            ProductFeatures object with extracted information
        """
        try:
            # Step 1: Load and prepare the image
            image_data = self._prepare_image(image_path)
            
            # Step 2: Send to AI for analysis
            analysis_result = self._call_vision_api(image_data)
            
            # Step 3: Convert AI response to our data structure
            features = self._parse_analysis_result(analysis_result)
            
            return features
            
        except Exception as e:
            # If anything goes wrong, we handle it gracefully
            print(f"Error analyzing image: {e}")
            # Return a basic result instead of crashing
            return ProductFeatures(
                name="Unknown Product",
                description="Could not analyze image",
                tags=["unprocessed"]
            )
    
    def _prepare_image(self, image_path: str) -> str:
        """
        Convert image to base64 format for API
        
        The underscore _ means this is a "private" method
        (only used inside this class)
        """
        # Open image file
        with open(image_path, "rb") as image_file:
            # Convert to base64 (text format for sending over internet)
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        return image_data
    
    def _call_vision_api(self, image_data: str) -> dict:
        """
        Send image to OpenAI Vision API for analysis
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # This is the prompt we send to the AI
        prompt = """
        Analyze this product image and extract the following information:
        - Product name
        - Category (clothing, electronics, home, etc.)
        - Primary color
        - Material (if visible)
        - Brand (if visible)
        - Detailed description
        - Relevant tags
        
        Respond in JSON format with these exact keys:
        name, category, color, material, brand, description, tags
        """
        
        payload = {
            "model": "gpt-4-vision-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}
                        }
                    ]
                }
            ],
            "max_tokens": 500
        }
        
        # Send request to OpenAI
        response = requests.post(self.base_url, headers=headers, json=payload)
        response.raise_for_status()  # Raises error if request failed
        
        return response.json()
    
    def _parse_analysis_result(self, api_response: dict) -> ProductFeatures:
        """
        Convert AI response to our ProductFeatures format
        """
        try:
            # Extract the AI's response text
            content = api_response["choices"][0]["message"]["content"]
            
            # Try to parse as JSON (AI should return structured data)
            import json
            parsed_data = json.loads(content)
            
            # Create ProductFeatures object from parsed data
            return ProductFeatures(
                name=parsed_data.get("name", "Unknown Product"),
                category=parsed_data.get("category"),
                color=parsed_data.get("color"),
                material=parsed_data.get("material"),
                brand=parsed_data.get("brand"),
                description=parsed_data.get("description", "No description available"),
                tags=parsed_data.get("tags", [])
            )
            
        except (json.JSONDecodeError, KeyError) as e:
            # If AI didn't return proper JSON, create a basic response
            print(f"Could not parse AI response: {e}")
            return ProductFeatures(
                name="Product Analysis Failed",
                description="AI response could not be parsed",
                tags=["parsing_error"]
            )


# Example of how to use this class:
if __name__ == "__main__":
    # This code only runs if you execute this file directly
    analyzer = ImageAnalyzer(api_key="your-openai-key")
    result = analyzer.analyze_image("path/to/product/image.jpg")
    print(f"Analyzed product: {result.name}")
    print(f"Description: {result.description}")