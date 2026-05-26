document.addEventListener('DOMContentLoaded', () => {
      const findLeadsBtn = document.getElementById('find-leads-btn');
      const saveSettingsBtn = document.getElementById('save-settings-btn');
      const leadsTbody = document.getElementById('leads-tbody');
      const loader = document.getElementById('loader');
      const scrapeNiche = document.getElementById('scrape-niche');

                              // IG Username/Password/API keys
                              const igUserInp = document.getElementById('ig-username');
      const igPassInp = document.getElementById('ig-password');
      const geminiKeyInp = document.getElementById('gemini-key');

                              // Load saved settings
                              fetch('/api/settings')
          .then(res => res.json())
          .then(data => {
                        if (data.username) igUserInp.value = data.username;
                        if (data.password) igPassInp.value = data.password;
                        if (data.gemini_key) geminiKeyInp.value = data.gemini_key;
          });

                              // Save Settings
                              saveSettingsBtn.addEventListener('click', async () => {
                                        const username = igUserInp.value.trim();
                                        const password = igPassInp.value.trim();
                                        const gemini_key = geminiKeyInp.value.trim();

                                                                       if (!username || !password || !gemini_key) {
                                                                                     alert('Please fill out all credential fields.');
                                                                                     return;
                                                                       }

                                                                       const res = await fetch('/api/settings', {
                                                                                     method: 'POST',
                                                                                     headers: { 'Content-Type': 'application/json' },
                                                                                     body: JSON.stringify({ username, password, gemini_key })
                                                                       });
                                        const data = await res.json();
                                        alert(data.message || 'Settings saved!');
                              });

                              // Fetch Leads
                              findLeadsBtn.addEventListener('click', async () => {
                                        loader.classList.remove('hidden');
                                        findLeadsBtn.disabled = true;

                                                                    try {
                                                                                  const niche = scrapeNiche.value;
                                                                                  const res = await fetch('/api/fetch-leads', {
                                                                                                    method: 'POST',
                                                                                                    headers: { 'Content-Type': 'application/json' },
                                                                                                    body: JSON.stringify({ niche })
                                                                                  });
                                                                                  const data = await res.json();

                                            if (data.error) {
                                                              alert('Error: ' + data.error);
                                                              return;
                                            }

                                            renderLeads(data.leads || []);
                                                                    } catch (err) {
                                                                                  alert('Failed to fetch leads: ' + err.message);
                                                                    } finally {
                                                                                  loader.classList.add('hidden');
                                                                                  findLeadsBtn.disabled = false;
                                                                    }
                              });

                              function renderLeads(leads) {
                                        if (leads.length === 0) {
                                                      leadsTbody.innerHTML = `<tr><td colspan="3" style="text-align: center; color: var(--text-muted); padding: 2rem;">No leads found. try saving credentials first!</td></tr>`;
                                                      return;
                                        }

          leadsTbody.innerHTML = leads.map(lead => {
                        const encodedMsg = encodeURIComponent(lead.ai_message || '');
                        const sendUrl = `https://wa.me/${lead.phone}?text=${encodedMsg}`;

                                                       return `
                                                                       <tr>
                                                                                           <td>
                                                                                                                   <div class="seller-card">
                                                                                                                                               <img class="seller-avatar" src="${lead.avatar_url || 'https://via.placeholder.com/150'}" alt="Avatar">
                                                                                                                                                                           <div class="seller-details">
                                                                                                                                                                                                           <span class="seller-name">${lead.full_name || lead.username}</span>
                                                                                                                                                                                                                                           <a class="seller-username" href="https://instagram.com/${lead.username}" target="_blank">@${lead.username}</a>
                                                                                                                                                                                                                                                                           <p class="bio-text">${lead.biography || 'No bio available'}</p>
                                                                                                                                                                                                                                                                                                       </div>
                                                                                                                                                                                                                                                                                                                               </div>
                                                                                                                                                                                                                                                                                                                                                   </td>
                                                                                                                                                                                                                                                                                                                                                                       <td class="message-cell">
                                                                                                                                                                                                                                                                                                                                                                                               <div class="message-bubble">${lead.ai_message || 'Drafting message...'}</div>
                                                                                                                                                                                                                                                                                                                                                                                                                   </td>
                                                                                                                                                                                                                                                                                                                                                                                                                                       <td>
                                                                                                                                                                                                                                                                                                                                                                                                                                                               <a href="${sendUrl}" target="_blank" class="btn secondary small send-btn" data-id="${lead.id}">Send DM</a>
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       <div>
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   <span class="status-badge ${lead.status === 'sent' ? 'sent' : 'unsent'}">${lead.status === 'sent' ? 'Sent' : 'Unsent'}</span>
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           </div>
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               </td>
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               </tr>
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           `;
          }).join('');

          // Add event listener to "Send DM" buttons to mark as sent
          document.querySelectorAll('.send-btn').forEach(btn => {
                        btn.addEventListener('click', async (e) => {
                                          const leadId = btn.getAttribute('data-id');
                                          // Optimistically update badge
                                                             const badge = btn.nextElementSibling.querySelector('.status-badge');
                                          badge.className = 'status-badge sent';
                                          badge.textContent = 'Sent';

                                                             // Send update to server
                                                             await fetch(`/api/mark-sent/${leadId}`, { method: 'POST' });
                        });
          });
                              }

                              // Initial load of existing leads
                              fetch('/api/leads')
          .then(res => res.json())
          .then(leads => {
                        if (leads && leads.length > 0) {
                                          renderLeads(leads);
                        }
          });
});
