"""Account messages use an explicit request locale; no ambient worker language."""
from apps.trips.services.customer_language import normalize_language

MESSAGES = {
    "en": {
        "welcome": "Welcome to Airport & City Transfer!",
        "welcome_body": "Hello {name},\n\nThank you for registering with Airport & City Transfer. Your account has been created and you can now book journeys.\n\nFor help, contact info@airportandcitytransfer.com.\n\nAirport & City Transfer",
        "reset": "Your ACT password reset code",
        "reset_body": "Hello {name},\n\nYour password reset code is: {code}\n\nThis code expires in 15 minutes. If you did not request a password reset, ignore this email. Do not share this code.\n\nAirport & City Transfer",
        "customer": "Customer",
    },
    "ar": {
        "welcome": "مرحبًا بك في Airport & City Transfer!",
        "welcome_body": "مرحبًا {name}،\n\nشكرًا لتسجيلك لدى Airport & City Transfer. تم إنشاء حسابك ويمكنك الآن حجز رحلاتك.\n\nللمساعدة، راسل info@airportandcitytransfer.com.\n\nAirport & City Transfer",
        "reset": "رمز إعادة تعيين كلمة مرور ACT",
        "reset_body": "مرحبًا {name}،\n\nرمز إعادة تعيين كلمة المرور هو: {code}\n\nتنتهي صلاحية الرمز بعد 15 دقيقة. إذا لم تطلب إعادة تعيين كلمة المرور، فتجاهل هذا البريد. لا تشارك هذا الرمز مع أي شخص.\n\nAirport & City Transfer",
        "customer": "عميلنا العزيز",
    },
    "fr": {
        "welcome": "Bienvenue chez Airport & City Transfer !",
        "welcome_body": "Bonjour {name},\n\nMerci de votre inscription chez Airport & City Transfer. Votre compte a été créé et vous pouvez désormais réserver vos trajets.\n\nPour obtenir de l’aide, contactez info@airportandcitytransfer.com.\n\nAirport & City Transfer",
        "reset": "Votre code de réinitialisation du mot de passe ACT",
        "reset_body": "Bonjour {name},\n\nVotre code de réinitialisation du mot de passe est : {code}\n\nCe code expire dans 15 minutes. Si vous n’avez pas demandé cette réinitialisation, ignorez cet e-mail. Ne partagez pas ce code.\n\nAirport & City Transfer",
        "customer": "cher client",
    },
    "de": {
        "welcome": "Willkommen bei Airport & City Transfer!",
        "welcome_body": "Hallo {name},\n\nvielen Dank für Ihre Registrierung bei Airport & City Transfer. Ihr Konto wurde erstellt. Sie können jetzt Fahrten buchen.\n\nBei Fragen wenden Sie sich an info@airportandcitytransfer.com.\n\nAirport & City Transfer",
        "reset": "Ihr Code zum Zurücksetzen des ACT-Passworts",
        "reset_body": "Hallo {name},\n\nIhr Code zum Zurücksetzen des Passworts lautet: {code}\n\nDieser Code läuft in 15 Minuten ab. Falls Sie das Zurücksetzen nicht angefordert haben, ignorieren Sie diese E-Mail. Geben Sie den Code nicht weiter.\n\nAirport & City Transfer",
        "customer": "lieber Kunde",
    },
    "es": {
        "welcome": "¡Le damos la bienvenida a Airport & City Transfer!",
        "welcome_body": "Hola {name}:\n\nGracias por registrarse en Airport & City Transfer. Su cuenta se ha creado y ya puede reservar viajes.\n\nSi necesita ayuda, contacte con info@airportandcitytransfer.com.\n\nAirport & City Transfer",
        "reset": "Su código para restablecer la contraseña de ACT",
        "reset_body": "Hola {name}:\n\nSu código para restablecer la contraseña es: {code}\n\nEste código caduca en 15 minutos. Si no ha solicitado restablecer la contraseña, ignore este correo. No comparta el código.\n\nAirport & City Transfer",
        "customer": "cliente",
    },
    "tr": {
        "welcome": "Airport & City Transfer’a hoş geldiniz!",
        "welcome_body": "Merhaba {name},\n\nAirport & City Transfer’a kaydolduğunuz için teşekkür ederiz. Hesabınız oluşturuldu; artık yolculuk rezervasyonu yapabilirsiniz.\n\nYardım için info@airportandcitytransfer.com adresine yazın.\n\nAirport & City Transfer",
        "reset": "ACT şifre sıfırlama kodunuz",
        "reset_body": "Merhaba {name},\n\nŞifre sıfırlama kodunuz: {code}\n\nBu kod 15 dakika sonra geçersiz olur. Şifre sıfırlama talebinde bulunmadıysanız bu e-postayı dikkate almayın. Kodu kimseyle paylaşmayın.\n\nAirport & City Transfer",
        "customer": "Değerli Müşterimiz",
    },
    "zh-CN": {
        "welcome": "欢迎使用 Airport & City Transfer！",
        "welcome_body": "{name}，您好：\n\n感谢您注册 Airport & City Transfer。您的账户已创建，现在可以预订行程。\n\n如需帮助，请联系 info@airportandcitytransfer.com。\n\nAirport & City Transfer",
        "reset": "您的 ACT 密码重置验证码",
        "reset_body": "{name}，您好：\n\n您的密码重置验证码为：{code}\n\n此验证码将在15分钟后失效。如果您未申请重置密码，请忽略此邮件。请勿向他人透露验证码。\n\nAirport & City Transfer",
        "customer": "尊敬的客户",
    },
}


def account_message(kind, user, locale="en", code=""):
    messages = MESSAGES[normalize_language(locale)]
    name = user.first_name or messages["customer"]
    return messages[kind], messages[kind + "_body"].format(name=name, code=code)
