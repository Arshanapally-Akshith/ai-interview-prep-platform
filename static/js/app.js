document.addEventListener('DOMContentLoaded', () => {
    const roleSelect = document.getElementById('role-select');
    const startBtn = document.getElementById('start-btn');
    const setupScreen = document.getElementById('setup-screen');
    const chatScreen = document.getElementById('chat-screen');
    const chatContainer = document.getElementById('chat-container');
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const currentRoleBadge = document.getElementById('current-role');
    const timerDisplay = document.getElementById('timer');

    let sessionId = null;
    let startTime = null;
    let timerInterval = null;

    // A dummy UUID for testing phase 1
    const userId = "123e4567-e89b-12d3-a456-426614174000";

    // Fetch roles
    fetch('/api/roles')
        .then(res => res.json())
        .then(roles => {
            roleSelect.innerHTML = '<option value="" disabled selected>Select a role...</option>';
            roles.forEach(role => {
                const option = document.createElement('option');
                option.value = role.id;
                option.textContent = role.name;
                roleSelect.appendChild(option);
            });
            startBtn.disabled = true;
        })
        .catch(err => console.error("Failed to load roles", err));

    roleSelect.addEventListener('change', () => {
        startBtn.disabled = !roleSelect.value;
    });

    startBtn.addEventListener('click', async () => {
        const roleId = roleSelect.value;
        const roleName = roleSelect.options[roleSelect.selectedIndex].text;
        
        try {
            startBtn.disabled = true;
            startBtn.textContent = "Starting...";

            const res = await fetch('/api/sessions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userId, role_id: roleId })
            });
            
            if (!res.ok) throw new Error("Failed to start session");
            
            const data = await res.json();
            sessionId = data.id;
            
            // Switch screens
            setupScreen.classList.remove('active');
            chatScreen.classList.active = true; // wait, the classList needs to be set properly
            chatScreen.classList.add('active');
            currentRoleBadge.textContent = roleName;
            
            // Start timer
            startTime = new Date();
            timerInterval = setInterval(updateTimer, 1000);
            
            // Add initial Maya message
            addMessage("Hi, I'm Maya. Let's get started. How are you doing today?", "maya");
            
        } catch (e) {
            alert(e.message);
            startBtn.disabled = false;
            startBtn.textContent = "Start Interview";
        }
    });

    function updateTimer() {
        const now = new Date();
        const diff = Math.floor((now - startTime) / 1000);
        const mins = Math.floor(diff / 60).toString().padStart(2, '0');
        const secs = (diff % 60).toString().padStart(2, '0');
        timerDisplay.textContent = `${mins}:${secs}`;
    }

    function addMessage(content, role) {
        const div = document.createElement('div');
        div.className = `message ${role}`;
        div.textContent = content;
        chatContainer.appendChild(div);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    async function sendMessage() {
        const text = messageInput.value.trim();
        if (!text || !sessionId) return;

        addMessage(text, "user");
        messageInput.value = '';
        messageInput.disabled = true;
        sendBtn.disabled = true;

        const typing = document.createElement('div');
        typing.className = "typing-indicator";
        typing.id = "typing";
        typing.textContent = "Maya is typing...";
        chatContainer.appendChild(typing);
        chatContainer.scrollTop = chatContainer.scrollHeight;

        try {
            const res = await fetch(`/api/sessions/${sessionId}/turn`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: text })
            });
            
            if (!res.ok) throw new Error("Network response was not ok");
            
            const data = await res.json();
            document.getElementById('typing').remove();
            addMessage(data.content, "maya");
        } catch (e) {
            document.getElementById('typing').remove();
            addMessage("Sorry, I encountered an error. Please try again.", "maya");
            console.error(e);
        } finally {
            messageInput.disabled = false;
            sendBtn.disabled = false;
            messageInput.focus();
        }
    }

    sendBtn.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
});
