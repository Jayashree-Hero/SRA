from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import os

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/index')
def index2():
    return render_template('index.html')

@app.route('/cae-analysis')
def cae_analysis():
    return render_template('cae-analysis.html')

@app.route('/overall_analytics')
def overall_analytics():
    return render_template('overall_analytics.html')

@app.route('/arrear_upload')
def arrear_analytics():
    return render_template('arrear_upload.html')

@app.route('/arrears')
def arrears():
    return render_template('arrears.html')

@app.route('/highest-marks')
def highest():
    return render_template('highest-marks.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)
    
    file = request.files['file']
    section = request.form.get('section')

    if file.filename == '' or not section:
        return redirect(request.url)  

    if file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{section}_{file.filename}")
        file.save(file_path)
        return redirect(url_for('analytics', filename=f"{section}_{file.filename}", section=section))

@app.route('/analytics/<filename>')
def analytics(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    data = pd.read_excel(file_path)

    data = data.replace('AB', pd.NA).apply(pd.to_numeric, errors='coerce')

    fail_mark = 25
    total_students = len(data)
    section = request.args.get('section', 'Unknown')
    arrear_counts = {1: 0, 2: 0, 3: 0, '4+': 0}  

    subject_metrics = {
        'Section': section,
        'Subject Code': [],
        'Total Absent': [],
        'Total Present': [],
        'Total Fail': [],
        'Total Pass': [],
        'Pass Percentage': []
    }

    for _, student_row in data.iterrows():
        arrear_count = 0
        for course_code in data.columns[4:]:
            mark = student_row[course_code]
            if pd.isna(mark) or mark < fail_mark:  
                arrear_count += 1
        if arrear_count in arrear_counts:
            arrear_counts[arrear_count] += 1
        elif arrear_count >= 4:  
            arrear_counts['4+'] += 1

    for subject in data.columns[3:]:  
        subject_data = data[subject]

        total_absent = subject_data.isna().sum()
        total_present = subject_data.notna().sum()
        total_fail = subject_data[subject_data < fail_mark].count()
        total_pass = total_present - total_fail
        pass_percentage = (total_pass / total_present * 100) if total_present > 0 else 0

        subject_metrics['Subject Code'].append(subject)
        subject_metrics['Total Absent'].append(total_absent)
        subject_metrics['Total Present'].append(total_present)
        subject_metrics['Total Fail'].append(total_fail)
        subject_metrics['Total Pass'].append(total_pass)
        subject_metrics['Pass Percentage'].append(round(pass_percentage, 3))

    subject_metrics_df = pd.DataFrame(subject_metrics)
    
    summary_statistics = {
        "Total Students": total_students,
        "Overall Pass Percentage": round(subject_metrics_df['Pass Percentage'].mean(), 3),
        "1 Arrear": arrear_counts[1],
        "2 Arrears": arrear_counts[2],
        "3 Arrears": arrear_counts[3],
        "4+ Arrears": arrear_counts['4+'] 
    }

    return render_template('analytics.html', 
                           tables=[subject_metrics_df.to_html(index=False)], 
                           summary=summary_statistics, 
                           section=section)


@app.route('/upload-overall', methods=['POST'])
def upload_overall():
    if 'marks_file' not in request.files or 'staff_file' not in request.files:
        return redirect(request.url)
    
    marks_file = request.files['marks_file']
    staff_file = request.files['staff_file']

    if marks_file.filename == '' or staff_file.filename == '':
        return redirect(request.url)

    if marks_file and staff_file:
        marks_path = os.path.join(app.config['UPLOAD_FOLDER'], marks_file.filename)
        staff_path = os.path.join(app.config['UPLOAD_FOLDER'], staff_file.filename)

        marks_file.save(marks_path)
        staff_file.save(staff_path)

        return redirect(url_for('view_overall_analytics', 
                                marks_filename=marks_file.filename, 
                                staff_filename=staff_file.filename))

@app.route('/view-overall-analytics/<marks_filename>/<staff_filename>')
def view_overall_analytics(marks_filename, staff_filename):
    marks_path = os.path.join(app.config['UPLOAD_FOLDER'], marks_filename)
    staff_path = os.path.join(app.config['UPLOAD_FOLDER'], staff_filename)

    try:
        marks_data = pd.read_excel(marks_path)
        staff_data = pd.read_excel(staff_path)
    except Exception as e:
        return f"Error reading files: {str(e)}", 500

    marks_data.columns = marks_data.columns.str.strip()


    if 'Section' not in marks_data.columns:
        return "The 'Section' column is missing. Please check the Excel file.", 400

    for column in marks_data.columns[4:]:
        marks_data[column] = pd.to_numeric(marks_data[column], errors='coerce')

    print("NaN values per column:\n", marks_data.isna().sum())

    analytics_data = {
        'Course Code': [], 'Name of Course': [], 'Section': [], 'Staff Handled': [],
        'Total Absent': [], 'Total Present': [], 'Total Fail': [], 
        'Total Pass': [], 'Pass Percentage': [], 'Overall Percentage': []
    }
    subject_count = len(staff_data['Course Code'].unique())
    section_count = len(marks_data['Section'].unique())  
    total_students = len(marks_data)
    arrear_counts = {1: 0, 2: 0, 3: 0, '4+': 0}

    for _, student_row in marks_data.iterrows():
        arrear_count = 0
        for course_code in marks_data.columns[4:]:
            mark = student_row[course_code]
            if pd.isna(mark) or mark < 25:  
                arrear_count += 1
        if arrear_count in arrear_counts:
            arrear_counts[arrear_count] += 1
        elif arrear_count >= 4: 
            arrear_counts['4+'] += 1

    for course_code in marks_data.columns[4:]:
        cumulative_pass_percentage = 0  
        for section in marks_data['Section'].unique():
            section_marks = marks_data[marks_data['Section'] == section][course_code]

            total_present = section_marks.notna().sum()
            total_absent = section_marks.isna().sum()
            total_fail = section_marks[section_marks < 25].count()
            total_pass = total_present - total_fail
            pass_percentage = (total_pass / total_present * 100) if total_present > 0 else 0
            staff_rows = staff_data[(staff_data['Course Code'] == course_code) & 
                                    (staff_data['Section'] == section)]

            for _, staff_row in staff_rows.iterrows():
                analytics_data['Course Code'].append(course_code)
                analytics_data['Name of Course'].append(staff_row['Course Name'])
                analytics_data['Section'].append(staff_row['Section'])
                analytics_data['Staff Handled'].append(staff_row['Staff Name'])
                analytics_data['Total Absent'].append(total_absent)
                analytics_data['Total Present'].append(total_present)
                analytics_data['Total Fail'].append(total_fail)
                analytics_data['Total Pass'].append(total_pass)
                analytics_data['Pass Percentage'].append(round(pass_percentage, 3))
            cumulative_pass_percentage += pass_percentage
        overall_pass_percentage = cumulative_pass_percentage / section_count
        overall_total_pass_percentage = cumulative_pass_percentage / subject_count
        for _ in range(section_count):
            analytics_data['Overall Percentage'].append(round(overall_pass_percentage,3))
    analytics_df = pd.DataFrame(analytics_data)

    if analytics_df.empty:
        return "No analytics data could be generated.", 400

    return render_template('view-overall-analytics.html',
                           tables=[analytics_df.to_html(classes='table table-striped', index=False)],
                           summary={
                               "Total Sections": section_count,
                               "Total Students": total_students,
                               "Overall Pass Percentage": overall_total_pass_percentage,
                               "1 Arrear": arrear_counts[1],
                               "2 Arrears": arrear_counts[2],
                               "3 Arrears": arrear_counts[3],
                               "4+ Arrears": arrear_counts['4+'],   
                           })

@app.route('/arrear_upload', methods=['GET', 'POST'])
def arrear_upload():
    if request.method == 'POST':
        if 'marks_file' not in request.files or 'staff_file' not in request.files:
            return redirect(request.url)

        marks_file = request.files['marks_file']
        staff_file = request.files['staff_file']

        if marks_file.filename == '' or staff_file.filename == '':
            return redirect(request.url)

        if marks_file and staff_file:
            marks_path = os.path.join(app.config['UPLOAD_FOLDER'], marks_file.filename)
            staff_path = os.path.join(app.config['UPLOAD_FOLDER'], staff_file.filename)

            marks_file.save(marks_path)
            staff_file.save(staff_path)

            return redirect(url_for('view_arrear_analytics',
                                    marks_filename=marks_file.filename,
                                    staff_filename=staff_file.filename))

    return render_template('arrear_upload.html')


@app.route('/view_arrear_analytics/<marks_filename>/<staff_filename>')
def view_arrear_analytics(marks_filename, staff_filename):
    marks_path = os.path.join(app.config['UPLOAD_FOLDER'], marks_filename)
    staff_path = os.path.join(app.config['UPLOAD_FOLDER'], staff_filename)

    try:
        marks_data = pd.read_excel(marks_path)
        staff_data = pd.read_excel(staff_path)
    except Exception as e:
        return f"Error reading files: {str(e)}", 500

    marks_data.columns = marks_data.columns.str.strip()


    if 'Section' not in marks_data.columns:
        return "The 'Section' column is missing. Please check the Excel file.", 400

    for column in marks_data.columns[4:]:
        marks_data[column] = pd.to_numeric(marks_data[column], errors='coerce')

    print("NaN values per column:\n", marks_data.isna().sum())

    analytics_data = {
        'Course Code': [], 'Name of Course': [], 'Section': [], 'Staff Handled': [],
        'Total Absent': [], 'Total Present': [], 'Total Fail': [], 
        'Total Pass': [], 'Pass Percentage': [], 'Overall Percentage': []
    }
    subject_count = len(staff_data['Course Code'].unique())
    section_count = len(marks_data['Section'].unique())  
    total_students = len(marks_data)
    arrear_counts = {1: 0, 2: 0, 3: 0, '4+': 0} 

    for _, student_row in marks_data.iterrows():
        arrear_count = 0
        for course_code in marks_data.columns[4:]:
            mark = student_row[course_code]
            if pd.isna(mark) or mark < 50:  
                arrear_count += 1
        if arrear_count in arrear_counts:
            arrear_counts[arrear_count] += 1
        elif arrear_count >= 4:  
            arrear_counts['4+'] += 1

    for _, student_row in marks_data.iterrows():
        arrear_count = 0
        for course_code in marks_data.columns[4:]:
            mark = student_row[course_code]
            if pd.isna(mark) or mark < 50:  
                arrear_count += 1
        if arrear_count in arrear_counts:
            arrear_counts[arrear_count] += 1

    for course_code in marks_data.columns[4:]:
        cumulative_pass_percentage = 0
        for section in marks_data['Section'].unique():
            section_marks = marks_data[marks_data['Section'] == section][course_code]

            total_present = section_marks.notna().sum()
            total_absent = section_marks.isna().sum()
            total_fail = section_marks[section_marks < 25].count()
            total_pass = total_present - total_fail
            pass_percentage = (total_pass / total_present * 100) if total_present > 0 else 0
            staff_rows = staff_data[(staff_data['Course Code'] == course_code) &
                                    (staff_data['Section'] == section)]

            for _, staff_row in staff_rows.iterrows():
                analytics_data['Course Code'].append(course_code)
                analytics_data['Name of Course'].append(staff_row['Course Name'])
                analytics_data['Section'].append(staff_row['Section'])
                analytics_data['Staff Handled'].append(staff_row['Staff Name'])
                analytics_data['Total Absent'].append(total_absent)
                analytics_data['Total Present'].append(total_present)
                analytics_data['Total Fail'].append(total_fail)
                analytics_data['Total Pass'].append(total_pass)
                analytics_data['Pass Percentage'].append(round(pass_percentage, 3))
            cumulative_pass_percentage += pass_percentage
        overall_pass_percentage = cumulative_pass_percentage / section_count
        overall_total_pass_percentage = cumulative_pass_percentage / subject_count
        for _ in range(section_count):
            analytics_data['Overall Percentage'].append(round(overall_pass_percentage, 3))
    analytics_df = pd.DataFrame(analytics_data)

    if analytics_df.empty:
        return "No analytics data could be generated.", 400

    return render_template(
        'view_arrear_upload.html',
        tables=[analytics_df.to_html(classes='table table-striped', index=False)],
        summary={
            "Total Sections": section_count,
            "Total Students": total_students,
            "Overall Pass Percentage": overall_total_pass_percentage,
            "1 Arrear": arrear_counts[1],
            "2 Arrears": arrear_counts[2],
            "3 Arrears": arrear_counts[3],
            "4+ Arrears": arrear_counts['4+']
        }
    )


@app.route('/arrears_up', methods=['GET', 'POST'])
def arrears_up_file():
    if request.method == 'POST':
        if 'marks_file' not in request.files:
            return redirect(request.url)

        marks_file = request.files['marks_file']

        if marks_file.filename == '':
            return redirect(request.url)

        if marks_file:
            marks_path = os.path.join(app.config['UPLOAD_FOLDER'], marks_file.filename)

            marks_file.save(marks_path)

            return redirect(url_for('arrears_Fif',
                                    marks_filename=marks_file.filename))
        

@app.route('/arrears_Fif/<marks_filename>')
def arrears_Fif(marks_filename):
    marks_path = os.path.join(app.config['UPLOAD_FOLDER'], marks_filename)
    try:
        marks_data = pd.read_excel(marks_path)
    except Exception as e:
        return f"Error reading files: {str(e)}", 500

    marks_data.columns = marks_data.columns.str.strip()

    if 'Section' not in marks_data.columns:
        return "The 'Section' column is missing. Please check the Excel file.", 400

    print(marks_data['Section'].head())

    marks_data['Section'] = marks_data['Section'].astype(str).str.strip().str.replace(r'\s+', '', regex=True)

    if marks_data['Section'].isna().sum() > 0:
        marks_data['Section'] = marks_data['Section'].fillna('Unknown')  

    for column in marks_data.columns[4:]:
        marks_data[column] = pd.to_numeric(marks_data[column], errors='coerce')

    arrear_students = [] 
    for _, student_row in marks_data.iterrows():
        arrear_count = 0
        for course_code in marks_data.columns[4:]:
            mark = student_row[course_code]
            if pd.isna(mark) or mark < 25:  
                arrear_count += 1
        if arrear_count > 0:
            arrear_students.append({
                'register_number': student_row['Reg. Number'],
                'student_name': student_row['Student Name'],
                'section': student_row['Section'],
                'arrears': arrear_count
            })

    return render_template('arrears_Fif.html', arrear_students=arrear_students)


@app.route('/arrears_upn', methods=['GET', 'POST'])
def arrears_upn_file():
    if request.method == 'POST':
        if 'marks_file' not in request.files:
            return redirect(request.url)

        marks_file = request.files['marks_file']

        if marks_file.filename == '':
            return redirect(request.url)

        if marks_file:
            marks_path = os.path.join(app.config['UPLOAD_FOLDER'], marks_file.filename)

            marks_file.save(marks_path)

            return redirect(url_for('arrears_hun',
                                    marks_filename=marks_file.filename))
        
@app.route('/arrears_hun/<marks_filename>')
def arrears_hun(marks_filename):
    marks_path = os.path.join(app.config['UPLOAD_FOLDER'], marks_filename)
    try:
        marks_data = pd.read_excel(marks_path)
    except Exception as e:
        return f"Error reading files: {str(e)}", 500

    marks_data.columns = marks_data.columns.str.strip()

    if 'Section' not in marks_data.columns:
        return "The 'Section' column is missing. Please check the Excel file.", 400

    print(marks_data['Section'].head())

    marks_data['Section'] = marks_data['Section'].astype(str).str.strip().str.replace(r'\s+', '', regex=True)

    if marks_data['Section'].isna().sum() > 0:
        marks_data['Section'] = marks_data['Section'].fillna('Unknown')  

    for column in marks_data.columns[4:]:
        marks_data[column] = pd.to_numeric(marks_data[column], errors='coerce')

    arrear_students = [] 
    for _, student_row in marks_data.iterrows():
        arrear_count = 0
        for course_code in marks_data.columns[4:]:
            mark = student_row[course_code]
            if pd.isna(mark) or mark < 50:  
                arrear_count += 1
        if arrear_count > 0:
            arrear_students.append({
                'register_number': student_row['Reg. Number'],
                'student_name': student_row['Student Name'],
                'section': student_row['Section'],
                'arrears': arrear_count
            })

    return render_template('arrears_hun.html', arrear_students=arrear_students)


@app.route('/highest_m', methods=['GET', 'POST'])
def highest_m():
    if request.method == 'POST':
        if 'marks_file' not in request.files:
            return redirect(request.url)

        marks_file = request.files['marks_file']

        if marks_file.filename == '':
            return redirect(request.url)

        if marks_file:
            marks_path = os.path.join(app.config['UPLOAD_FOLDER'], marks_file.filename)

            marks_file.save(marks_path)

            return redirect(url_for('highest_mark',
                                    marks_filename=marks_file.filename))
        
        
@app.route('/highest-mark/<marks_filename>')
def highest_mark(marks_filename):
    marks_path = os.path.join(app.config['UPLOAD_FOLDER'], marks_filename)
    try:
        marks_data = pd.read_excel(marks_path)
    except Exception as e:
        return f"Error reading files: {str(e)}", 500

    marks_data.columns = marks_data.columns.str.strip()

    if 'Section' not in marks_data.columns or 'Reg. Number' not in marks_data.columns or 'Student Name' not in marks_data.columns:
        return "Required columns are missing. Please check the Excel file.", 400

    marks_data['Section'] = marks_data['Section'].astype(str).str.strip().str.replace(r'\s+', '', regex=True)

    if marks_data['Section'].isna().sum() > 0:
        marks_data['Section'] = marks_data['Section'].fillna('Unknown')

    for column in marks_data.columns[4:]:
        marks_data[column] = pd.to_numeric(marks_data[column], errors='coerce')

    marks_data['Total Marks'] = marks_data.iloc[:, 4:].sum(axis=1)

    top_students = marks_data.sort_values(by='Total Marks', ascending=False).head(30)

    top_30_students = []
    for _, student_row in top_students.iterrows():
        top_30_students.append({
            'register_number': student_row['Reg. Number'],
            'student_name': student_row['Student Name'],
            'section': student_row['Section'],
            'total_marks': student_row['Total Marks']
        })

    return render_template('highest-mark.html', top_30_students=top_30_students)


@app.route('/highest_ma', methods=['GET', 'POST'])
def highest_ma():
    if request.method == 'POST':
        if 'marks_file' not in request.files:
            return redirect(request.url)

        marks_file = request.files['marks_file']

        if marks_file.filename == '':
            return redirect(request.url)

        if marks_file:
            marks_path = os.path.join(app.config['UPLOAD_FOLDER'], marks_file.filename)

            marks_file.save(marks_path)

            return redirect(url_for('highest_mark_u',
                                    marks_filename=marks_file.filename))
        
        
@app.route('/highest_mark/<marks_filename>')
def highest_mark_u(marks_filename):
    marks_path = os.path.join(app.config['UPLOAD_FOLDER'], marks_filename)
    try:
        marks_data = pd.read_excel(marks_path)
    except Exception as e:
        return f"Error reading files: {str(e)}", 500

    marks_data.columns = marks_data.columns.str.strip()

    if 'Section' not in marks_data.columns or 'Reg. Number' not in marks_data.columns or 'Student Name' not in marks_data.columns:
        return "Required columns are missing. Please check the Excel file.", 400

    marks_data['Section'] = marks_data['Section'].astype(str).str.strip().str.replace(r'\s+', '', regex=True)

    if marks_data['Section'].isna().sum() > 0:
        marks_data['Section'] = marks_data['Section'].fillna('Unknown')

    for column in marks_data.columns[4:]:
        marks_data[column] = pd.to_numeric(marks_data[column], errors='coerce')

    marks_data['Total Marks'] = marks_data.iloc[:, 4:].sum(axis=1)

    top_students = marks_data.sort_values(by='Total Marks', ascending=False).head(30)

    top_30_students = []
    for _, student_row in top_students.iterrows():
        top_30_students.append({
            'register_number': student_row['Reg. Number'],
            'student_name': student_row['Student Name'],
            'section': student_row['Section'],
            'total_marks': student_row['Total Marks']
        })

    return render_template('highest_mark.html', top_30_students=top_30_students)


if __name__ == '__main__':
    app.run(debug=True)

