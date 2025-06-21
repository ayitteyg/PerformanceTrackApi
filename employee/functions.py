import json
from datetime import datetime
import decimal
from django.db.models import Model
import pandas as pd
from django.core.exceptions import ValidationError


def convert_decimal(obj):
    """Custom function to handle JSON serialization of special types."""
    if isinstance(obj, decimal.Decimal):
        return float(obj)  # Convert Decimal to float
    elif isinstance(obj, datetime.date):  
        return obj.isoformat()  # Convert date to string (YYYY-MM-DD)
    elif isinstance(obj, datetime):  
        return obj.isoformat()  # Convert datetime to string (YYYY-MM-DDTHH:MM:SS)
    elif isinstance(obj, Model):  # Handle Django model instances
        return {field.name: getattr(obj, field.name) for field in obj._meta.fields}  # Convert model to dict
    
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


import json
from datetime import datetime, date
import decimal
from django.db.models import Model
from django.core.serializers import serialize
from django.core.exceptions import ValidationError

def convert_decimal(obj):
    """
    Custom JSON serializer that handles:
    - Decimal → float
    - Date/datetime → ISO string
    - Django Model → dict of fields
    - QuerySet → list of dicts
    """
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    elif isinstance(obj, date):  # Handles both date and datetime
        return obj.isoformat()
    elif isinstance(obj, Model):
        return model_to_dict(obj)
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
        return list(obj)  # Convert querysets/iterables to list
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def model_to_dict(instance):
    """Helper to convert model instance to dict including related fields"""
    from django.forms.models import model_to_dict
    data = model_to_dict(instance)
    for field in instance._meta.get_fields():
        if field.is_relation and field.many_to_one and field.related_model:
            if getattr(instance, field.name):
                data[field.name] = model_to_dict(getattr(instance, field.name))
    return data




months = {
    1: 'January',
    2: 'February',
    3: 'March',
    4: 'April',
    5: 'May',
    6: 'June',
    7: 'July',
    8: 'August',
    9: 'September',
    10: 'October',
    11: 'November',
    12: 'December',
}

quarters = {
    1: 'Q1',
    2: 'Q2',
    3: 'Q3',
    4: 'Q4',
}


years = list(range(2020, datetime.now().year + 1))



from django.db import transaction

def reset_model_data(model):
    """
    Completely resets all data in the given Django model.
    
    Args:
        model: Django model class to reset
    
    Returns:
        tuple: (number of objects deleted, dict with deletion counts)
    """
    try:
        with transaction.atomic():
            # Delete all objects in the model
            deletion_info = model.objects.all().delete()
            return deletion_info
    except Exception as e:
        # Handle any potential errors
        print(f"Error resetting model {model.__name__}: {str(e)}")
        raise
    
    

def print_model_objects(model, limit=50, fields=None):
    """
    Prints all objects in the given Django model for debugging.
    
    Args:
        model: Django model class
        limit: Maximum number of objects to display (default: 50)
        fields: Specific fields to display (None shows all fields)
    """
    queryset = model.objects.all()
    count = queryset.count()
    
    print(f"\n=== Debugging model: {model.__name__} ===")
    print(f"Total objects: {count}")
    
    if count == 0:
        print("No objects found in the model.")
        return
    
    print("\nFirst {} objects:".format(min(limit, count)))
    
    # Get field names if not specified
    if fields is None:
        fields = [field.name for field in model._meta.fields]
    
    # Print header
    header = " | ".join(fields)
    print("\n" + header)
    print("-" * len(header))
    
    # Print objects
    for obj in queryset[:limit]:
        values = []
        for field in fields:
            try:
                value = str(getattr(obj, field))
                values.append(value[:50] + "..." if len(value) > 50 else value)
            except AttributeError:
                values.append("<field error>")
        print(" | ".join(values))



def excel_to_json(file_path, output_path=None):
    """
    Convert Excel file to JSON format with specific formatting rules:
    - Dates converted to date-only strings (YYYY-MM-DD)
    - Contact numbers converted to strings with leading zeros preserved
    - NaN values replaced with None (null in JSON)
    - Strips extra spaces from column names

    Args:
        file_path (str): Path to Excel file
        output_path (str, optional): Path to save JSON file. If None, returns JSON data

    Returns:
        dict/list: JSON data if output_path is None, otherwise saves to file
    """
    try:
        # Read Excel file
        df = pd.read_excel(file_path)

        # Clean column names (strip whitespace)
        df.columns = df.columns.str.strip()

        # Convert date fields to date-only format
        date_columns = df.select_dtypes(include=['datetime64', 'datetime64[ns]']).columns
        for col in date_columns:
            df[col] = df[col].dt.strftime('%Y-%m-%d')

        # Convert contact numbers to proper string format
        if 'contact' in df.columns:
            def format_contact(x):
                if pd.isna(x):
                    return ''
                try:
                    # Handle both float and int inputs
                    num = int(float(x))
                    return f"{num:010d}"  # Formats with leading zeros to make 10 digits
                except (ValueError, TypeError):
                    return str(x).strip()  # Fallback to string if conversion fails

            df['contact'] = df['contact'].apply(format_contact)

        # Replace NaN values with None
       # Replace NaN with empty string
        df = df.fillna('')

        # Convert to list of dictionaries
        json_data = df.to_dict(orient='records')

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=4, ensure_ascii=False)
            return True

        return json_data

    except Exception as e:
        raise ValidationError(f"Error converting Excel to JSON: {str(e)}")



def load_json_to_model(json_data, model, mapping=None, update_existing=False):
    """
    Load JSON data into Django model with proper type conversion:
    - Handles date strings
    - Preserves contact number formatting

    Args:
        json_data (str/dict/list): JSON data or file path
        model (django.db.models.Model): Model class to load into
        mapping (dict, optional): Field mapping between JSON and model
        update_existing (bool): Update existing records if True

    Returns:
        tuple: (success_count, error_count, errors)
    """
    # Load JSON data
    if isinstance(json_data, str):
        try:
            with open(json_data) as f:
                data = json.load(f)
        except FileNotFoundError:
            try:
                data = json.loads(json_data)
            except json.JSONDecodeError:
                raise ValidationError("Invalid JSON data or file path")
    else:
        data = json_data if isinstance(json_data, list) else [json_data]

    success_count = 0
    error_count = 0
    errors = []
    instances = []

    with transaction.atomic():
        for record in data:
            try:
                model_fields = {f.name for f in model._meta.get_fields()}
                mapped_data = {}

                # Apply field mapping if provided
                if mapping:
                    for json_field, model_field in mapping.items():
                        if model_field in model_fields:
                            mapped_data[model_field] = record.get(json_field)
                else:
                    for field in record:
                        if field in model_fields:
                            mapped_data[field] = record[field]

                # Convert date strings to date objects
                if 'date' in mapped_data and isinstance(mapped_data['date'], str):
                    try:
                        mapped_data['date'] = datetime.strptime(mapped_data['date'], '%Y-%m-%d').date()
                    except ValueError:
                        # Try fallback format or slice datetime string
                        mapped_data['date'] = datetime.strptime(mapped_data['date'][:10], '%Y-%m-%d').date()

                # Format contact number as string
                if 'contact' in mapped_data and mapped_data['contact']:
                    if isinstance(mapped_data['contact'], (int, float)):
                        mapped_data['contact'] = str(int(mapped_data['contact']))
                    mapped_data['contact'] = mapped_data['contact'].zfill(10)

                # Update or create record
                if update_existing and 'id' in mapped_data:
                    instance, _ = model.objects.update_or_create(
                        id=mapped_data['id'],
                        defaults=mapped_data
                    )
                else:
                    instance = model(**mapped_data)
                    instance.full_clean()
                    instances.append(instance)

                success_count += 1

            except Exception as e:
                error_count += 1
                errors.append({
                    'record': record,
                    'error': str(e)
                })

        # Bulk create if not updating
        if not update_existing and instances:
            model.objects.bulk_create(instances)

    return success_count, error_count, errors


def convert_to_json(file):
    excel_to_json(f'data_excel/{file}.xlsx', f'data_json/{file}.json')

def read_file (file):
    with open(f'data_json/{file}.json', 'r') as f:
        member_data = json.load(f)
        for data in member_data:
            print(data['contact'])

def load_json_model(file, model):
    success, errors, error_log = load_json_to_model(f'data_json/{file}.json', model)
    print(f"{success} imported successfully, {errors} failed.")

    for err in error_log:
        print("Error with record:", err['record'])
        print("Error message:", err['error'])
        print("-" * 50)