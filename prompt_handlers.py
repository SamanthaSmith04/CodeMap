# prompt_handlers.py

def handle_specific_file(template_config):
    file_path = input("Enter the specific file path to explain (e.g. src/utils.py): ").strip()
    if not file_path:
        print("No file path provided. Using general overview instead.")
        return template_config['prompt'], None  # return prompt and None for file_path

    enhanced_prompt = (
        template_config['prompt'] +
        f"\nFocus ONLY on the file: '{file_path}'.\n"
        "Explain what this file does at a high level, its role in the system, "
        "and its key responsibilities. Ignore all other files."
    )
    return enhanced_prompt, file_path