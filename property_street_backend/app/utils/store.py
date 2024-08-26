import resend
import importlib.resources as files
from string import Template


resend.api_key = "re_ZiJG94e2_3Y8QW4MuBrpGbHyDdQcdYWVX"


def send_email(from_email, from_name, subject, to_email,  html_email, to_name=None, reply_to_email=None, text_email=None, cc=None, bcc=None, attachments=None):
    params = {
        "from": f'{from_name} <{from_email}>',
        "to": [to_email],
        "subject": subject,
        "html": html_email
    }
    return resend.Emails.send(params)
    
    
def read_email_from_html_template_name(template_name):
    try:
        # Define the package where your email templates are located
        package = 'property_street_backend.app.utils.email_templates'
        
        # Construct the template file name
        template_filename = f"{template_name}.html"
        
        # Use importlib.resources to read the template file
        with files(package).joinpath(template_filename).open('r', encoding='utf-8') as f:
            template_content = f.read()
        
        return template_content
    except Exception as e:
        print(f"Error reading email template: {e}")
        return None

def substituted_string(context: str, map: dict) -> str:
    """
    This function takes a string called the context, 
    and substitutes snippets in content with key based mechanism.
    The corresponding value of that key should be  present in map which is a dictionary
    """
    string_template=Template(context)
    response=string_template.substitute(map)
    return response