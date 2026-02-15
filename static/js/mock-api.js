/**
 * Mock API for Local UI/UX Testing
 * Simulates backend responses without requiring deployed functions
 */

(function() {
    'use strict';

    // Mock data store
    const mockDB = {
        homework: [
            {
                id: '1',
                subject: 'Mathematics',
                title: 'Algebra Exercise - Chapter 5',
                description: 'Complete exercises 1-10 on page 45. Focus on quadratic equations.',
                due_date: new Date(Date.now() + 86400000 * 2).toISOString(),
                status: 'pending',
                priority: 'high',
                student_name: 'Ahmad'
            },
            {
                id: '2',
                subject: 'Science',
                title: 'Plant Biology Worksheet',
                description: 'Label the parts of a flower and write their functions.',
                due_date: new Date(Date.now() + 86400000 * 5).toISOString(),
                status: 'pending',
                priority: 'medium',
                student_name: 'Ahmad'
            },
            {
                id: '3',
                subject: 'Bahasa Melayu',
                title: 'Karangan - Hari Kemerdekaan',
                description: 'Write a 200-word essay about Independence Day.',
                due_date: new Date(Date.now() - 86400000).toISOString(),
                status: 'overdue',
                priority: 'high',
                student_name: 'Aisyah'
            }
        ],
        user: {
            id: 'user-1',
            name: 'Parent User',
            role: 'parent',
            language: 'en',
            children: [
                { id: 'c1', name: 'Ahmad', class: '5A', school: 'SK Taman Bunga Raya' },
                { id: 'c2', name: 'Aisyah', class: '3B', school: 'SK Taman Bunga Raya' }
            ]
        },
        stats: {
            total_homework: 12,
            completed: 8,
            pending: 3,
            overdue: 1,
            completion_rate: 67
        }
    };

    // Mock API responses
    const mockAPI = {
        'GET /api/health': () => ({
            status: 'healthy',
            version: '1.0.0-local',
            timestamp: new Date().toISOString(),
            environment: 'local-static',
            services: { database: 'mock', telegram: 'not_configured', ai: ['gemini'] }
        }),

        'GET /api/v1/homework': () => ({
            homework: mockDB.homework,
            total: mockDB.homework.length
        }),

        'POST /api/v1/homework': (data) => {
            const newHomework = {
                id: Date.now().toString(),
                ...data,
                status: 'pending',
                created_at: new Date().toISOString()
            };
            mockDB.homework.push(newHomework);
            return { id: newHomework.id, created: true };
        },

        'GET /api/v1/users/:id': () => mockDB.user,

        'GET /api/v1/students/:id/homework': () => ({
            student_id: 'student-1',
            homework: mockDB.homework
        }),

        'GET /api/v1/students/:id/stats': () => mockDB.stats,

        'PATCH /api/v1/homework/:id/complete': (data, id) => {
            const hw = mockDB.homework.find(h => h.id === id);
            if (hw) {
                hw.status = 'completed';
                hw.completed_at = new Date().toISOString();
            }
            return { id, status: 'completed' };
        }
    };

    // Intercept fetch requests
    const originalFetch = window.fetch;
    window.fetch = async function(url, options = {}) {
        const method = options.method || 'GET';
        const urlStr = url.toString();
        
        if (urlStr.includes('/api/') || urlStr.includes('/webhook/')) {
            console.log('[MockAPI]', method, urlStr);
            
            const urlObj = new URL(urlStr, window.location.origin);
            const path = urlObj.pathname;
            
            let key = `${method} ${path}`;
            let handler = mockAPI[key];
            
            if (!handler) {
                const patterns = Object.keys(mockAPI).filter(k => k.includes('/:'));
                for (const pattern of patterns) {
                    const regex = new RegExp('^' + pattern.replace(/:\w+/g, '([^/]+)') + '$');
                    const match = path.match(regex);
                    if (match && pattern.startsWith(method)) {
                        handler = mockAPI[pattern];
                        break;
                    }
                }
            }
            
            if (handler) {
                await new Promise(r => setTimeout(r, 100 + Math.random() * 200));
                
                let body = {};
                if (options.body) {
                    try { body = JSON.parse(options.body); } catch (e) { body = options.body; }
                }
                
                const responseData = handler(body, path.split('/').pop());
                
                return new Response(JSON.stringify(responseData), {
                    status: 200,
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Mock-API': 'true'
                    }
                });
            }
            
            return new Response(JSON.stringify({ error: 'Not found (mock)' }), {
                status: 404,
                headers: { 'Content-Type': 'application/json' }
            });
        }
        
        return originalFetch.apply(this, arguments);
    };

    console.log('🎭 Mock API loaded - Backend calls will be simulated');
    window.mockDB = mockDB;
    window.mockAPI = mockAPI;
})();
