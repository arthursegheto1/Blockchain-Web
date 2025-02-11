async function createTransaction(port) {
    const amount = document.getElementById(`amount${port}`).value;
    const sender = document.getElementById(`sender${port}`).value;
    const recipient = document.getElementById(`recipient${port}`).value;

    if (!amount || !sender || !recipient) {
        alert("Preencha todos os campos!");
        return;
    }

    const transactionData = { sender, recipient, amount: parseFloat(amount) };

    try {
        const response = await fetch(`http://127.0.0.1:${port}/transactions/new`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(transactionData),
        });

        if (response.ok) {
            alert(`Transação enviada para a porta ${port}`);
            mine(port)
        } else {
            alert("Erro ao enviar transação.");
        }
    } catch (error) {
        alert("Erro ao conectar-se ao servidor.");
    }
}

async function mine(port) {
    try {
        await fetch(`http://127.0.0.1:${port}/mine`, {
            method: "GET",
            headers: { "Content-Type": "application/json" }
        })
            .then(response => {
                console.log(response.data)
            })
    } catch (error) {
        console.log(error)
    }
}

// Atualiza a blockchain automaticamente a cada 5 segundos
async function updateBlockchain() {
    const ports = [5000, 5001, 5002];
    document.getElementById("blockchain-container").innerHTML = "";

    for (const port of ports) {
        try {
            const response = await fetch(`http://127.0.0.1:${port}/chain`);
            if (!response.ok) continue;

            const data = await response.json();

            data.chain.forEach(block => {
                const blockDiv = document.createElement("div");
                blockDiv.classList.add("block");

                blockDiv.innerHTML = `
                    <p><strong>Porta:</strong> ${port}</p>
                    <p><strong>Index:</strong> ${block.index}</p>
                    <p><strong>Hash Anterior:</strong> ${block.previous_hash.substring(0, 15)}...</p>
                    <button class="show-transactions" onclick='showTransactions(${JSON.stringify(block.transactions)})'>
                        Mostrar transações
                    </button>
                `;
                document.getElementById("blockchain-container").appendChild(blockDiv);
            });
        } catch (error) {
            console.error(`Erro ao buscar dados da porta ${port}`);
        }
    }
}

function showTransactions(transactions) {
    alert(JSON.stringify(transactions, null, 2));
}

setInterval(updateBlockchain, 5000); // Atualiza a blockchain automaticamente