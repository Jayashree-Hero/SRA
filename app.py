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

@app.route('/student-details')
def student_analytics():
    return render_template('student-details.html')

@app.route('/cae-analysis')
def cae_analysis():
    return render_template('cae-analysis.html')

@app.route('/overall_analytics')
def overall_analytics():
    return render_template('overall_analytics.html')

# Upload Section Data
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)
    
    file = request.files['file']
    section = request.form.get('section')

    if file.filename == '' or not section:
        return redirect(request.url)  # Ensure valid file and section

    if file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{section}_{file.filename}")
        file.save(file_path)
        return redirect(url_for('analytics', filename=f"{section}_{file.filename}", section=section))

@app.route('/analytics/<filename>')
def analytics(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    data = pd.read_excel(file_path)

    # Replace 'AB' or non-numeric values with NaN
    data = data.replace('AB', pd.NA).apply(pd.to_numeric, errors='coerce')

    fail_mark = 25
    total_students = len(data)
    section = request.args.get('section', 'Unknown')

    subject_metrics = {
        'Section': section,
        'Subject Code': [],
        'Total Absent': [],
        'Total Present': [],
        'Total Fail': [],
        'Total Pass': [],
        'Pass Percentage': []
    }

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
        subject_metrics['Pass Percentage'].append(round(pass_percentage, 3))#.applymap(lambda x: f"{x:.3f}" if isinstance(x, (int, float))else x)

    subject_metrics_df = pd.DataFrame(subject_metrics)
    #subject_metrics_df = subject_metrics_df.map(lambda x: f"{x:.3f}" if isinstance(x, (int, float))else x)
    summary_statistics = {
        "Total Students": total_students,
        "Overall Pass Percentage": round(subject_metrics_df['Pass Percentage'].mean(), 3)
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
                           })

if __name__ == '__main__':
    app.run(debug=True)

