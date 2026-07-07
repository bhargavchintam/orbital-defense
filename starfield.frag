#version 120

uniform vec2 u_resolution;
uniform float u_time;

float rand(vec2 st){
    return fract(sin(dot(st.xy, vec2(12.9898, 78.233))) * 43758.5453);
}

float starLayer(vec2 uv, float gridScale, float speed, float probability, float maxBrightness){
    vec2 gridUV = uv * gridScale;
    gridUV.y -= u_time * speed;

    vec2 id = floor(gridUV);
    vec2 localUV = fract(gridUV);

    float cellRand = rand(id);
    float star = 0.0;

    if (cellRand < probability) {
        vec2 offset = vec2(rand(id + 10.0), rand(id + 20.0)) * 0.8 + 0.1;
        float dist = length(localUV - offset);
        float size = mix(0.01, 0.035, rand(id + 30.0));
        star = smoothstep(size, size * 0.5, dist);
        float twinkle = sin(u_time * 3.0 + cellRand * 10.0) * 0.5 + 0.5;
        star *= mix(0.5, 1.0, twinkle);
    }
    return star * maxBrightness;
}

void main(){
    vec2 uv = gl_FragCoord.xy / u_resolution.xy;
    uv.x *= u_resolution.x / u_resolution.y;
    vec3 finalColor = vec3(0.0);
    finalColor += starLayer(uv, 40.0, 0.2, 0.15, 0.4);
    finalColor += starLayer(uv, 20.0, 0.5, 0.08, 0.7);
    finalColor += starLayer(uv, 10.0, 1.2, 0.03, 1.0);
    vec3 spaceColor = mix(vec3(0.0, 0.0, 0.05), vec3(0.02, 0.0, 0.1), uv.y);
    finalColor += spaceColor;

    gl_FragColor = vec4(finalColor, 1.0);
}
