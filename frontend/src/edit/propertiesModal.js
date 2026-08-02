// A minimal modal prompting for the non-geometry fields a newly-drawn
// feature needs before it can be saved (e.g. a StudyArea's label/project).
// Not a full admin-form clone — just enough for the map dashboard's create
// flow to have somewhere to collect required fields.
export function promptForFields(title, fields) {
  return new Promise((resolve) => {
    const overlay = document.createElement('div');
    overlay.className = 'edit-modal-overlay';

    const modal = document.createElement('div');
    modal.className = 'edit-modal';

    const heading = document.createElement('h3');
    heading.textContent = title;
    modal.append(heading);

    const inputs = {};
    fields.forEach((field) => {
      const label = document.createElement('label');
      label.className = 'edit-modal-field';
      const span = document.createElement('span');
      span.textContent = field.label;
      label.append(span);

      let input;
      if (field.type === 'select') {
        input = document.createElement('select');
        field.options.forEach((opt) => {
          const option = document.createElement('option');
          option.value = opt.value;
          option.textContent = opt.label;
          input.append(option);
        });
      } else {
        input = document.createElement('input');
        input.type = 'text';
      }
      label.append(input);
      modal.append(label);
      inputs[field.name] = input;
    });

    const actions = document.createElement('div');
    actions.className = 'edit-modal-actions';
    const cancelBtn = document.createElement('button');
    cancelBtn.type = 'button';
    cancelBtn.textContent = 'Cancel';
    const saveBtn = document.createElement('button');
    saveBtn.type = 'button';
    saveBtn.className = 'edit-modal-save';
    saveBtn.textContent = 'Save';
    actions.append(cancelBtn, saveBtn);
    modal.append(actions);

    overlay.append(modal);
    document.body.append(overlay);
    inputs[fields[0]?.name]?.focus();

    function cleanup() {
      overlay.remove();
    }

    cancelBtn.addEventListener('click', () => {
      cleanup();
      resolve(null);
    });

    saveBtn.addEventListener('click', () => {
      const values = {};
      for (const field of fields) {
        const raw = inputs[field.name].value.trim();
        if (field.required !== false && !raw) {
          inputs[field.name].focus();
          return;
        }
        values[field.name] = field.type === 'select' ? Number(raw) || raw : raw;
      }
      cleanup();
      resolve(values);
    });
  });
}
