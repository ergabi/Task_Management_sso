from flask import Flask, redirect, render_template, url_for, request, abort, session 
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth
import requests ,os
from flask_wtf import FlaskForm
from wtforms import SelectField, TextAreaField, FileField, SubmitField
from wtforms.validators import DataRequired

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:VijiEd@localhost/Gabriel_Rajan'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  

appConf = {
    "OAUTH2_CLIENT_ID": os.getenv("OAUTH2_CLIENT_ID"),
    "OAUTH2_CLIENT_SECRET": os.getenv("OAUTH2_CLIENT_SECRET"),
    "OAUTH2_META_URL": "https://accounts.google.com/.well-known/openid-configuration",
    "FLASK_SECRET": os.getenv("FLASK_SECRET"),
    "FLASK_PORT": 5000
}


app.secret_key = appConf.get("FLASK_SECRET")

oauth = OAuth(app)

oauth.register("CHECKING",
               client_id=appConf.get("OAUTH2_CLIENT_ID"),
               client_secret=appConf.get("OAUTH2_CLIENT_SECRET"),
               server_metadata_url=appConf.get("OAUTH2_META_URL"),
               client_kwargs={
                   "scope": "openid profile email https://www.googleapis.com/auth/user.birthday.read https://www.googleapis.com/auth/user.gender.read https://www.googleapis.com/auth/userinfo.profile"
               }
            )

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    def __repr__(self):
        return f'<User {self.name}>'

class testModule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    selected_module = db.Column(db.String(100), nullable=True)
    manual_module = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f'<testModule {self.selected_module} - {self.manual_module}>'
    
class records(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    selected_module = db.Column(db.String(100), nullable=True)  
    text_area = db.Column(db.String(200), nullable=True)  
    description = db.Column(db.String(500), nullable=True)  
    attached_file_name = db.Column(db.String(200), nullable=True) 
    def __repr__(self):
        return f'<records {self.select} - {self.text_area} - {self.description} - {self.attached_file_name}>'

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return render_template('home.html', session=session.get("user"), indent=4)

@app.route('/google-login')
def googlelogin():
    return oauth.CHECKING.authorize_redirect(redirect_uri=url_for("googleCallback", _external=True))

@app.route("/signin-google")
def googleCallback():
    token = oauth.CHECKING.authorize_access_token()
    if not token:
        abort(400, description="Failed to retrieve token")
    
    personDataUrl = "https://people.googleapis.com/v1/people/me?personFields=names,birthdays,genders"

    personData = requests.get(
        personDataUrl,
        headers={
            "Authorization": f"Bearer {token['access_token']}"
        }
    )
    if personData.status_code != 200:
        abort(400, description="Failed to retrieve user information")

    personDataJson = personData.json()
    names = personDataJson.get("names", [])
    username = names[0].get("displayName", "User") if names else "User"
    session["user"] = username

    return redirect(url_for("dashboard", username=username))

@app.route('/dashboard')
def dashboard():
    username = session.get("user", "Guest")
    modules = testModule.query.all()
    record_all = records.query.all()
    return render_template('dashboard.html', username=username, save_modules=modules,select_Modules=modules,records =record_all)

@app.route('/save_module', methods=['POST'])
def save_module():
    if request.method == 'POST':
        selected_module = request.form.get('selected_module')
        manual_module = request.form.get('manual_module')
        action = request.form.get('action')
        
        existing_module = db.session.query(testModule).filter_by(selected_module=selected_module).first()
        
        if existing_module:
            new_manual_module = testModule(selected_module=existing_module.selected_module, manual_module=manual_module)
            db.session.add(new_manual_module)
            db.session.commit()
        
        else:
            new_module = testModule(selected_module=selected_module, manual_module=manual_module)
            db.session.add(new_module)
            db.session.commit()

        return redirect(url_for('dashboard'))
    
@app.route('/edit/<int:id>', methods=['POST'])
def edit_module(id):
    module = testModule.query.filter_by(id=id).first()  
    if module:  
        selected_module = request.form['selected_module'].strip()
        manual_module = request.form['manual_module'].strip()
        module.selected_module = selected_module
        module.manual_module = manual_module
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/delete/<int:id>', methods=['POST'])
def delete_module(id):
    module = testModule.query.filter_by(id=id).first()
    if module:
        db.session.delete(module)
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()  
    return redirect(url_for('home'))

class RecordForm(FlaskForm):
    select_module = SelectField('Select Module', choices=[], validators=[DataRequired()])
    text_area = TextAreaField('Text Area', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    file_upload = FileField('File Upload')
    submit = SubmitField('Save')
    cancel = SubmitField('Cancel')
    
@app.route('/form', methods=['GET', 'POST'])
def Formrecord():
    username = session.get("user", "Guest")
    modules = testModule.query.all()
    form = RecordForm()
    form.select_module.choices = [(module.id, module.selected_module) for module in modules]
    
    if form.validate_on_submit():
        file = form.file_upload.data
        upload_folder = 'static/uploads'
        os.makedirs(upload_folder, exist_ok=True)
        
        if file:
            file_path = os.path.join(upload_folder, file.filename)  
            file.save(file_path)
        
        new_record = records(selected_module=form.select_module.data, text_area=form.text_area.data, description=form.description.data, attached_file_name=file.filename)

  
        db.session.add(new_record)
        db.session.commit()
        
        return redirect(url_for('dashboard'))
    
    return render_template('form.html', form=form, username=username)

@app.route('/edit/<int:id>', methods=['POST'])
def edit_record(id):
    record = records.query.filter_by(id=id).first()   
    if record:
        selected_module = request.form['selected_module'].strip()
        text_area = request.form['text_area'].strip()
        description = request.form['description'].strip()
        attached_file_name = request.form['attached_file_name'].strip()
        record.selected_module = selected_module
        record.text_area = text_area
        record.description = description
        record.attached_file_name = attached_file_name
        db.session.commit()
        
    return redirect(url_for('dashboard'))

@app.route('/delete/<int:id>', methods=['POST'])
def delete_record(id):
    record = records.query.filter_by(id=id).first()  
    if record:
        db.session.delete(record)
        db.session.commit()
        
    return redirect(url_for('dashboard'))
     

if __name__ == '__main__':
    app.run(port=appConf.get("FLASK_PORT"), debug=True)
