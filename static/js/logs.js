document.addEventListener('DOMContentLoaded', function() {
    const daysOldSelect = document.getElementById('days_old_select');
    const dateRangeInputs = document.getElementById('date_range_inputs');

    daysOldSelect.addEventListener('change', function() {
        if (this.value === 'dates') {
            dateRangeInputs.style.display = 'flex';
        } else {
            dateRangeInputs.style.display = 'none';
            dateRangeInputs.querySelector('input[name="clear_start_date"]').value = '';
            dateRangeInputs.querySelector('input[name="clear_end_date"]').value = '';
        }
    });
});