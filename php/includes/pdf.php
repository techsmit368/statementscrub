<?php
function extract_pdf_text(string $filepath): string {
    // Try pdftotext first (available on most Linux hosts)
    if (function_exists('shell_exec') && !in_array('shell_exec', array_map('trim', explode(',', ini_get('disable_functions'))))) {
        $escaped = escapeshellarg($filepath);
        $text = shell_exec("pdftotext -layout $escaped -");
        if ($text && strlen(trim($text)) > 50) {
            return clean_text($text);
        }
    }

    // Fallback: read raw PDF bytes and extract text-like content
    return extract_pdf_raw($filepath);
}

function extract_pdf_raw(string $filepath): string {
    $content = file_get_contents($filepath);
    if (!$content) return '';

    // Extract text between BT/ET markers (PDF text blocks)
    $text = '';
    if (preg_match_all('/BT\s*(.*?)\s*ET/s', $content, $matches)) {
        foreach ($matches[1] as $block) {
            // Extract strings in parentheses: (text)
            if (preg_match_all('/\(([^)\\\\]*(?:\\\\.[^)\\\\]*)*)\)\s*T[jJ]/', $block, $strings)) {
                foreach ($strings[1] as $s) {
                    $s = stripcslashes($s);
                    if (trim($s)) $text .= $s . ' ';
                }
            }
        }
    }

    // Also try hex strings <...>
    if (preg_match_all('/<([0-9A-Fa-f]+)>\s*T[jJ]/', $content, $hex_matches)) {
        foreach ($hex_matches[1] as $hex) {
            $decoded = hex_to_str($hex);
            if (trim($decoded)) $text .= $decoded . ' ';
        }
    }

    return clean_text($text);
}

function hex_to_str(string $hex): string {
    $str = '';
    for ($i = 0; $i < strlen($hex) - 1; $i += 2) {
        $str .= chr(hexdec(substr($hex, $i, 2)));
    }
    return preg_replace('/[^\x20-\x7E]/', '', $str);
}

function clean_text(string $text): string {
    $text = preg_replace('/\r\n|\r/', "\n", $text);
    $text = preg_replace('/\n{3,}/', "\n\n", $text);
    $text = preg_replace('/[ \t]{3,}/', '  ', $text);
    return trim($text);
}

function truncate_text(string $text, int $max_chars = 40000): string {
    if (strlen($text) <= $max_chars) return $text;
    $start = (int)($max_chars * 0.8);
    $end   = (int)($max_chars * 0.15);
    return substr($text, 0, $start) . "\n...[truncated]...\n" . substr($text, -$end);
}
