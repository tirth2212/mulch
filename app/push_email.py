import smtplib
from email.message import EmailMessage

# Email config
sender_email = 'tirth@mulchinstalled.com'
receiver_email = 'sam@mulchinstalled.com'
subject = 'Here is your schedule for tomorrow!'
body = 'Attached is the text file.'
password = 'Tirth1234'

# Create email message
msg = EmailMessage()
msg['From'] = sender_email
msg['To'] = receiver_email
msg['Subject'] = subject
msg.set_content(body)

# Attach the text file
file_path = 'truck_schedule_output.txt'
with open(file_path, 'rb') as file:
    file_data = file.read()
    file_name = file_path.split('/')[-1]
    msg.add_attachment(file_data, maintype='text', subtype='plain', filename=file_name)

# Send the email via SMTP
with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
    smtp.login(sender_email, password)
    smtp.send_message(msg)

print('Email sent successfully!')
