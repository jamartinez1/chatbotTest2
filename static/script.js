document.addEventListener('DOMContentLoaded', function() {
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const chatMessages = document.getElementById('chat-messages');
    const contactForm = document.getElementById('contact-form');
    const contactName = document.getElementById('contact-name');
    const contactEmail = document.getElementById('contact-email');
    const contactOrganization = document.getElementById('contact-organization');
    const submitContact = document.getElementById('submit-contact');

    function addMessage(content, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
        messageDiv.innerHTML = `<strong>${isUser ? 'Tú:' : 'Bot:'}</strong> ${content}`;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function showContactForm() {
        contactForm.style.display = 'block';
        contactName.focus();
    }

    function hideContactForm() {
        contactForm.style.display = 'none';
        contactName.value = '';
        contactEmail.value = '';
        contactOrganization.value = '';
    }

    function sendMessage() {
        const question = userInput.value.trim();
        if (!question) return;

        addMessage(question, true);
        userInput.value = '';

        fetch('/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ question: question }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                addMessage(`Error: ${data.error}`);
            } else {
                addMessage(data.answer);
                // Verificar si la respuesta requiere contacto adicional
                if (data.requires_contact && !data.answer.toLowerCase().includes('¡hola! soy un asistente experto')) {
                    showContactForm();
                }
            }
        })
        .catch(error => {
            addMessage('Error al conectar con el servidor.');
            console.error('Error:', error);
        });
    }

    function sendContact() {
        const name = contactName.value.trim();
        const email = contactEmail.value.trim();
        const organization = contactOrganization.value.trim();
        if (!name || !email || !organization) return;

        fetch('/contact', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name: name, email: email, organization: organization }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                addMessage('Gracias por proporcionar tus datos de contacto. Nos pondremos en contacto contigo pronto.');
                hideContactForm();
            } else {
                addMessage(`Error: ${data.error || 'undefined'}`);
                // Mantener el formulario visible para que el usuario pueda corregir
            }
        })
        .catch(error => {
            addMessage('Error al conectar con el servidor.');
            console.error('Error:', error);
        });
    }

    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    submitContact.addEventListener('click', sendContact);
    contactEmail.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendContact();
        }
    });
});