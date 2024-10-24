const ctx = document.getElementById('myChart').getContext('2d');

// Initialize chart with default values
const chart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [], // Labels will be updated dynamically
        datasets: [
            {
                label: 'Budget',
                data: [], // Data will be updated dynamically
                borderColor: 'red',
                backgroundColor: 'rgba(255, 0, 0, 0.1)',
                borderWidth: 2
            },
            {
                label: 'Spending',
                data: [], // Data will be updated dynamically
                borderColor: 'blue',
                backgroundColor: 'rgba(0, 0, 255, 0.1)',
                borderWidth: 2
            }
        ]
    },
    options: {
        scales: {
            y: {
                beginAtZero: true
            }
        },
        plugins: {
            tooltip: {
                callbacks: {
                    label: function(tooltipItem) {
                        const amount = tooltipItem.raw; // Get the raw value (spending amount)
                        const index = tooltipItem.dataIndex; // Get the index for the spending purposes
                        const purpose = spendingPurposes[index] || ''; // Get the purpose corresponding to the amount
                        return [`Amount: $${amount}`, `Purpose: ${purpose}`];
                    }
                }
            }
        }
    }
});

// Variables to store purposes
let spendingPurposes = [];

// Fetch initial chart data from the server
async function fetchChartData() {
    try {
        dropdown = document.getElementById("settings");
        var response;

        if (dropdown.value != "" && dropdown.value != 0){
            console.log(dropdown.value);
            response = await fetch(`/dashboardData?budget_id=${dropdown.value}`);

        }

        else{
            console.log("empty");
            response = await fetch('/dashboardData');
        }

        const data = await response.json();
        budget_data = data["budget"];
        spending_data = data["spending"];

        budgetList = data["allBudgets"]
        budgetList.forEach(budget => {
            availableOptions = document.getElementById(budget._id)
            if (availableOptions == null) {
                option = document.createElement("option");
                option.id = budget._id;
                option.value = budget._id;
                option.textContent = `Start Date: ${budget.start_date} Duration: ${budget.duration} Amount: $${budget.budget}`;
                dropdown.appendChild(option);
            }

        })

        const duration = parseInt(budget_data["duration"]); // Duration in days
        const amount = parseFloat(budget_data["budget"]);

        const labels = Array.from({ length: duration + 1 }, (_, i) => `Day ${i}`);

        const dataset2Data = Array.from({ length: duration + 1 }, (_, i) => (i * amount / duration).toFixed(2));

        const dataset3Data = Array(duration + 1).fill(0);
        spendingPurposes = Array(duration + 1).fill('');
        spending_data.forEach(i => {
            const day = i["day"];
            const spentAmount = parseFloat(i["amount"]);
            const purpose = i["purpose"];
            if (day <= duration) {
                dataset3Data[day] = spentAmount;
                spendingPurposes[day] = purpose;
            }
        });

        chart.data.labels = labels;
        chart.data.datasets[0].data = dataset2Data;
        chart.data.datasets[1].data = dataset3Data;
        chart.update();


    } catch (error) {
        console.error('Error fetching chart data:', error);
    }
}

// Initialize the chart with data on page load
document.addEventListener('DOMContentLoaded', fetchChartData);
document.getElementById("settings").addEventListener("change", fetchChartData);

// Get modals
const budgetModal = document.getElementById("budgetModal");
const spendingModal = document.getElementById("spendingModal");

// Get buttons
const createBudgetBtn = document.getElementById("createBudgetBtn");
const logSpendingBtn = document.getElementById("logSpendingBtn");

// Get <span> elements to close modals
const closeBudgetModal = document.getElementById("closeBudgetModal");
const closeSpendingModal = document.getElementById("closeSpendingModal");

// Open Create Budget modal
createBudgetBtn.onclick = function () {
    budgetModal.style.display = "block";
}

// Open Log Spending modal
logSpendingBtn.onclick = function () {
    spendingModal.style.display = "block";
}

// Close modals
closeBudgetModal.onclick = function () {
    budgetModal.style.display = "none";
}
closeSpendingModal.onclick = function () {
    spendingModal.style.display = "none";
}

// Close modal when clicking outside of it
window.onclick = function (event) {
    if (event.target === budgetModal) {
        budgetModal.style.display = "none";
    }
    if (event.target === spendingModal) {
        spendingModal.style.display = "none";
    }
}

// Handle budget form submission
document.getElementById("budgetForm").onsubmit = async function (event) {
    event.preventDefault();

    const duration = parseInt(document.getElementById('duration').value); // Duration in days
    const amount = parseFloat(document.getElementById('amount').value);

    const labels = Array.from({ length: duration + 1 }, (_, i) => `Day ${i}`);

    const dataset2Data = Array.from({ length: duration + 1 }, (_, i) => (i * amount / duration).toFixed(2));

    const dataset3Data = Array(duration + 1).fill(0);

    chart.data.labels = labels;
    chart.data.datasets[0].data = dataset2Data;
    chart.data.datasets[1].data = dataset3Data;
    chart.update();

    // Close the modal
    budgetModal.style.display = "none";

    let formData = new FormData(this);
    let data = { startDate: formData.get("startDate"), duration: formData.get("duration"), budget: formData.get("budget") };

    try {
        let response = await fetch("/createBudget", {
            method: "POST",
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            alert("Budget Created Successfully!");
            fetchChartData();
        } else {
            alert("Cannot Create Budget.");
        }
    } catch (error) {
        alert("Error: " + error.message);
    }
}

// Handle spending form submission
document.getElementById("spendingForm").onsubmit = async function (event) {
    event.preventDefault(); // Prevent form from submitting normally

    const date = document.getElementById('date').value;
    const spentAmount = parseFloat(document.getElementById('spent').value);

    if (!date || isNaN(spentAmount)) {
        alert("Please provide valid data.");
        return;
    }

    spendingModal.style.display = "none";

    let formData = new FormData(this);
    let data = { date: formData.get("date"), spent: formData.get("spent"), purpose: formData.get("purpose") };

    try {
        let response = await fetch("/spendingBudget", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            alert("Spending Logged Successfully!");
            // Re-fetch data to update the chart
            fetchChartData();
        } else {
            alert("Error, Spending Not Logged.");
        }
    } catch (error) {
        alert("Error: " + error.message);
    }
}