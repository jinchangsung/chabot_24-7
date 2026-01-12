/**
 * chat.js
 * 실시간 대화 처리 및 UX 개선 로직
 */

$(document).ready(function() {

    // 1. 메시지를 화면에 추가하는 함수 (마크다운 및 줄바꿈 개선)
    function appendMessage(role, text, isThinking = false) {
        let html = '';
        if (role === 'user') {
            html = `<div class="msg-wrapper user-wrapper"><div class="message user">${text}</div></div>`;
        } else {
            // GPT의 응답 스타일(볼드체, 목록 등)을 지원하기 위해 정규식으로 간단한 마킹 처리
            let formattedText = text
                .replace(/\n/g, '<br>') // 줄바꿈
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // 볼드체 (**텍스트**)
                .replace(/^\d+\.\s/gm, '<br>• '); // 번호 목록을 불렛으로 변환

            html = `
                <div class="msg-wrapper bot-wrapper ${isThinking ? 'thinking' : ''}">
                    <img src="${BOT_ICON_URL}" class="chat-icon">
                    <div class="message bot">${formattedText}</div>
                </div>`;
        }
        
        // 생각 중인 메시지가 이미 있다면 제거하고 추가
        if (!isThinking) {
            $('.thinking').remove();
        }

        $('#chat-box').append(html);
        
        // 부드러운 하단 스크롤
        $('#chat-box').animate({ scrollTop: $('#chat-box')[0].scrollHeight }, 300);
    }

    // 2. 서버로 메시지를 전송하는 메인 함수
    function sendMessage() {
        const msgInput = $('#user-input');
        const msg = msgInput.val().trim();
        
        if (!msg) return;

        // 사용자 메시지 표시
        appendMessage('user', msg);
        msgInput.val(''); 

        // 봇이 생각 중임을 표시 (UX 개선)
        // 주인님이 구축하신 지식 창고에서 데이터를 검색하는 동안 표시됩니다.
        appendMessage('bot', '지식 창고에서 답변을 찾는 중입니다...', true);

        $.ajax({
            url: '/chat',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ message: msg }),
            success: function(data) {
                // 실제 응답으로 교체
                appendMessage('bot', data.reply);
            },
            error: function(xhr, status, error) {
                $('.thinking').remove(); // 에러 시 로딩 아이콘 제거
                console.error("Chat Error:", error);
                appendMessage('bot', '죄송합니다. 서버와 연결이 원활하지 않습니다. 잠시 후 다시 시도해 주세요.');
            }
        });
    }

    // --- 이벤트 리스너 ---

    $('#send-btn').click(sendMessage);

    $('#user-input').on('keydown', function(e) {
        if (e.which == 13 && !e.shiftKey) { // Enter키 (Shift+Enter는 줄바꿈 허용)
            e.preventDefault();
            sendMessage();
        }
    });
});