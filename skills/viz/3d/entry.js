// v3d.html에 묶이는 three.js 부분. 장면 정의에서 쓰는 이름은 모두 window.T3로 나간다.
// 새 클래스가 필요하면 여기에 더하고 `npm run build:v3d`로 다시 묶는다.
import {
  WebGLRenderer, Scene, PerspectiveCamera, OrthographicCamera, HemisphereLight, DirectionalLight, AmbientLight, PointLight,
  Group, Object3D, Mesh, InstancedMesh, Line, LineSegments, Points, Sprite,
  BufferGeometry, Float32BufferAttribute, PlaneGeometry, BoxGeometry, CylinderGeometry, SphereGeometry, ConeGeometry,
  TorusGeometry, RingGeometry, CircleGeometry, TubeGeometry, ExtrudeGeometry, LatheGeometry, EdgesGeometry, Shape, Path,
  CatmullRomCurve3, ShadowMaterial, MeshStandardMaterial, MeshBasicMaterial, MeshLambertMaterial, LineBasicMaterial,
  LineDashedMaterial, PointsMaterial, SpriteMaterial, CanvasTexture, Vector2, Vector3, Color, Euler, Quaternion,
  MathUtils, Timer, DoubleSide, GridHelper, ArrowHelper
} from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

window.T3 = {
  WebGLRenderer, Scene, PerspectiveCamera, OrthographicCamera, HemisphereLight, DirectionalLight, AmbientLight, PointLight,
  Group, Object3D, Mesh, InstancedMesh, Line, LineSegments, Points, Sprite,
  BufferGeometry, Float32BufferAttribute, PlaneGeometry, BoxGeometry, CylinderGeometry, SphereGeometry, ConeGeometry,
  TorusGeometry, RingGeometry, CircleGeometry, TubeGeometry, ExtrudeGeometry, LatheGeometry, EdgesGeometry, Shape, Path,
  CatmullRomCurve3, ShadowMaterial, MeshStandardMaterial, MeshBasicMaterial, MeshLambertMaterial, LineBasicMaterial,
  LineDashedMaterial, PointsMaterial, SpriteMaterial, CanvasTexture, Vector2, Vector3, Color, Euler, Quaternion,
  MathUtils, Timer, DoubleSide, GridHelper, ArrowHelper, OrbitControls
};
