from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
import json

diet_plan_bp = Blueprint('diet_plan', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_diet_plan(health_data, report_content=None):
    """
    Generate personalized diet plan based on health data and optional report
    This is a placeholder - in production, you'd use AI/ML models
    """
    age = int(health_data.get('age', 25))
    weight = float(health_data.get('weight', 70))
    height = float(health_data.get('height', 170))
    activity_level = health_data.get('activityLevel', 'moderate')
    dietary_preference = health_data.get('dietaryPreference', 'none')
    health_conditions = health_data.get('healthConditions', '').lower()
    
    # Calculate BMI
    bmi = weight / ((height / 100) ** 2)
    
    # Base meals
    breakfast = []
    lunch = []
    dinner = []
    snacks = []
    recommendations = []
    restrictions = []
    
    # Customize based on dietary preference
    if dietary_preference == 'vegetarian' or dietary_preference == 'vegan':
        breakfast = [
            "Oatmeal with berries and nuts (300 cal)",
            "Whole grain toast with avocado (250 cal)",
            "Green smoothie with spinach and banana (200 cal)"
        ]
        lunch = [
            "Quinoa salad with chickpeas and vegetables (400 cal)",
            "Lentil soup with whole grain bread (350 cal)",
            "Mixed green salad with tofu (300 cal)"
        ]
        dinner = [
            "Grilled vegetable stir-fry with brown rice (450 cal)",
            "Black bean tacos with guacamole (400 cal)",
            "Vegetable curry with quinoa (420 cal)"
        ]
        snacks = [
            "Apple with almond butter (150 cal)",
            "Carrot sticks with hummus (100 cal)",
            "Mixed nuts and dried fruits (200 cal)"
        ]
    else:
        breakfast = [
            "Scrambled eggs with whole grain toast (350 cal)",
            "Greek yogurt with granola and berries (300 cal)",
            "Protein smoothie with banana (280 cal)"
        ]
        lunch = [
            "Grilled chicken salad with olive oil dressing (450 cal)",
            "Salmon with quinoa and steamed vegetables (500 cal)",
            "Turkey sandwich on whole grain bread (400 cal)"
        ]
        dinner = [
            "Baked fish with sweet potato and broccoli (480 cal)",
            "Lean beef stir-fry with brown rice (520 cal)",
            "Grilled chicken with roasted vegetables (450 cal)"
        ]
        snacks = [
            "Hard-boiled eggs (140 cal)",
            "Greek yogurt (120 cal)",
            "Protein bar (200 cal)"
        ]
    
    # Add recommendations based on activity level
    if activity_level == 'sedentary':
        recommendations.append("Focus on portion control - aim for 1,800-2,000 calories daily")
        recommendations.append("Increase fiber intake with vegetables and whole grains")
    elif activity_level in ['active', 'extreme']:
        recommendations.append("Increase protein intake to support muscle recovery")
        recommendations.append("Aim for 2,500-3,000 calories daily with focus on complex carbs")
        recommendations.append("Stay hydrated - drink at least 3 liters of water daily")
    else:
        recommendations.append("Maintain balanced diet with 2,000-2,200 calories daily")
        recommendations.append("Include protein with every meal")
    
    # Add health condition-specific recommendations
    if 'diabetes' in health_conditions or 'blood sugar' in health_conditions:
        recommendations.append("Monitor carbohydrate intake - choose complex carbs over simple sugars")
        recommendations.append("Eat smaller, frequent meals to maintain stable blood sugar")
        restrictions.append("Avoid refined sugars, white bread, and sugary drinks")
        restrictions.append("Limit high-glycemic index foods like white rice and potatoes")
    
    if 'high blood pressure' in health_conditions or 'hypertension' in health_conditions:
        recommendations.append("Reduce sodium intake to less than 2,300mg per day")
        recommendations.append("Increase potassium-rich foods like bananas and spinach")
        restrictions.append("Avoid processed foods high in sodium")
        restrictions.append("Limit caffeine and alcohol consumption")
    
    if 'cholesterol' in health_conditions:
        recommendations.append("Increase omega-3 fatty acids from fish and nuts")
        recommendations.append("Focus on fiber-rich foods to help lower cholesterol")
        restrictions.append("Avoid trans fats and limit saturated fats")
        restrictions.append("Reduce red meat consumption")
    
    if 'lactose' in health_conditions:
        restrictions.append("Avoid dairy products or use lactose-free alternatives")
        recommendations.append("Consider calcium supplementation or fortified plant milk")
    
    # BMI-based recommendations
    if bmi < 18.5:
        recommendations.append("Focus on calorie-dense, nutrient-rich foods to gain weight healthily")
        recommendations.append("Add healthy fats like nuts, avocados, and olive oil")
    elif bmi > 25:
        recommendations.append("Create a moderate calorie deficit for healthy weight loss")
        recommendations.append("Focus on high-volume, low-calorie foods like vegetables")
        recommendations.append("Practice mindful eating and portion control")
    
    # General recommendations
    recommendations.append("Drink at least 8 glasses of water daily")
    recommendations.append("Include a variety of colorful vegetables in your meals")
    recommendations.append("Limit processed foods and added sugars")
    
    return {
        'breakfast': breakfast,
        'lunch': lunch,
        'dinner': dinner,
        'snacks': snacks,
        'recommendations': recommendations,
        'restrictions': restrictions
    }


@diet_plan_bp.route('/diet-plan', methods=['POST'])
def create_diet_plan():
    """Generate personalized diet plan"""
    try:
        # Check if request has file
        report_file = None
        if 'report' in request.files:
            file = request.files['report']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # In production, you'd process this file
                # For now, we'll just acknowledge it was uploaded
                report_file = filename
        
        # Get health data
        health_data_str = request.form.get('healthData')
        if not health_data_str:
            return jsonify({'error': 'Missing health data'}), 400
        
        health_data = json.loads(health_data_str)
        
        # Validate required fields
        required_fields = ['age', 'weight', 'height', 'activityLevel', 'dietaryPreference']
        for field in required_fields:
            if field not in health_data or not health_data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Generate diet plan
        diet_plan = generate_diet_plan(health_data, report_file)
        
        return jsonify({
            'message': 'Diet plan generated successfully',
            'dietPlan': diet_plan,
            'reportUploaded': report_file is not None
        }), 200
        
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON in health data'}), 400
    except Exception as e:
        print(f"Error generating diet plan: {str(e)}")
        return jsonify({'error': 'Failed to generate diet plan'}), 500


@diet_plan_bp.route('/diet-plan/validate', methods=['POST'])
def validate_health_data():
    """Validate health data before generating plan"""
    try:
        data = request.get_json()
        
        errors = []
        
        # Validate age
        if 'age' in data:
            age = int(data['age'])
            if age < 1 or age > 120:
                errors.append('Age must be between 1 and 120')
        
        # Validate weight
        if 'weight' in data:
            weight = float(data['weight'])
            if weight < 20 or weight > 300:
                errors.append('Weight must be between 20 and 300 kg')
        
        # Validate height
        if 'height' in data:
            height = float(data['height'])
            if height < 50 or height > 250:
                errors.append('Height must be between 50 and 250 cm')
        
        if errors:
            return jsonify({'valid': False, 'errors': errors}), 400
        
        return jsonify({'valid': True, 'message': 'Health data is valid'}), 200
        
    except ValueError:
        return jsonify({'valid': False, 'errors': ['Invalid number format']}), 400
    except Exception as e:
        print(f"Error validating health data: {str(e)}")
        return jsonify({'error': 'Validation failed'}), 500