import os
import pandas as pd
from flask import Flask, request, jsonify, send_from_directory
import asyncio
from telegram import Bot

app = Flask(__name__, static_folder='.')

TOKEN = "8921622193:AAEdQ8zlhKc9-uUYYy8edid9v3fD8s7Tb28"
bot = Bot(token=TOKEN)

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/process-groups', methods=['POST'])
def process_groups():
    teacher_contact = request.form.get('teacher_contact', '').strip()
    mode = request.form.get('mode', 'individual')
    custom_group_name = request.form.get('custom_group_name', 'Student Class Group').strip()
    
    if not teacher_contact:
        return jsonify({"message": "Error: Teacher contact is required."}), 400

    try:
        teacher_id = int(teacher_contact)
    except ValueError:
        teacher_id = teacher_contact

    students_data = []

    # Handle Excel file upload
    if 'file' in request.files and request.files['file'].filename != '':
        file = request.files['file']
        try:
            df = pd.read_excel(file)
            df.columns = [str(col).strip().lower() for col in df.columns]
            for _, row in df.iterrows():
                name = str(row.get('name', '')).strip()
                p_id = str(row.get('parent_id', '')).strip()
                if name and p_id:
                    students_data.append((name, p_id))
        except Exception as e:
            return jsonify({"message": f"Error reading Excel file: {str(e)}"}), 400

    # Handle Manual Text Input
    elif 'manual_text' in request.form:
        lines = request.form['manual_text'].strip().split('\n')
        for line in lines:
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 2:
                students_data.append((parts[0], parts[1]))

    if not students_data:
        return jsonify({"message": "Error: No valid student records found."}), 400

    success_count = 0

    async def execute_group_creation():
        nonlocal success_count
        
        if mode == 'individual':
            for student_name, parent_str in students_data:
                try:
                    parent_id = int(parent_str)
                except ValueError:
                    continue

                group_title = f"{student_name}"
                try:
                    chat = await bot.create_chat(title=group_title)
                    chat_id = chat.id

                    await bot.add_chat_member(chat_id=chat_id, user_id=parent_id)
                    if isinstance(teacher_id, int):
                        await bot.add_chat_member(chat_id=chat_id, user_id=teacher_id)
                    
                    success_count += 1
                except Exception as e:
                    print(f"Failed group for {student_name}: {e}")

        elif mode == 'unified':
            group_title = custom_group_name if custom_group_name else "Student Group"
            try:
                chat = await bot.create_chat(title=group_title)
                chat_id = chat.id

                if isinstance(teacher_id, int):
                    try:
                        await bot.add_chat_member(chat_id=chat_id, user_id=teacher_id)
                    except Exception:
                        pass

                for _, parent_str in students_data:
                    try:
                        parent_id = int(parent_str)
                        await bot.add_chat_member(chat_id=chat_id, user_id=parent_id)
                        success_count += 1
                    except Exception as e:
                        print(f"Failed adding parent {parent_str}: {e}")
                
                success_count = 1
            except Exception as e:
                print(f"Failed unified group creation: {e}")

    asyncio.run(execute_group_creation())

    if mode == 'individual':
        return jsonify({"message": f"Successfully created {success_count} individual student groups!"})
    else:
        return jsonify({"message": f"Successfully created unified group '{custom_group_name}' with all members!"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)