import ObjectTags from '@/components/ai/ObjectTags.vue';
import type { DetectedObject } from '@/types/image';
import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';

function makeObject(overrides: Partial<DetectedObject> = {}): DetectedObject {
  return {
    id: 'obj-1',
    class_name: 'dog',
    confidence: 0.9,
    bounding_box: [0, 0, 10, 10],
    ...overrides,
  };
}

function badgeTexts(wrapper: ReturnType<typeof mount>) {
  return wrapper.findAll('[data-slot="badge"]').map((b) => b.text());
}

describe('ObjectTags', () => {
  it('shows a placeholder and no badges when there are no objects', () => {
    const wrapper = mount(ObjectTags, { props: { objects: [] } });

    expect(wrapper.text()).toBe('No objects detected');
    expect(badgeTexts(wrapper)).toEqual([]);
  });

  it('renders one badge per object with class name and confidence', () => {
    const wrapper = mount(ObjectTags, {
      props: {
        objects: [
          makeObject({ id: 'a', class_name: 'dog', confidence: 0.9 }),
          makeObject({ id: 'b', class_name: 'cat', confidence: 0.6 }),
        ],
      },
    });

    expect(badgeTexts(wrapper)).toEqual(['dog 90%', 'cat 60%']);
    expect(wrapper.text()).not.toContain('No objects detected');
  });

  it('sorts objects by confidence, highest first', () => {
    const wrapper = mount(ObjectTags, {
      props: {
        objects: [
          makeObject({ id: 'a', class_name: 'cup', confidence: 0.4 }),
          makeObject({ id: 'b', class_name: 'person', confidence: 0.95 }),
          makeObject({ id: 'c', class_name: 'chair', confidence: 0.7 }),
        ],
      },
    });

    expect(badgeTexts(wrapper)).toEqual(['person 95%', 'chair 70%', 'cup 40%']);
  });

  it.each([
    [0.876, '88%'],
    [0.874, '87%'],
    [1, '100%'],
    [0.004, '0%'],
  ])('rounds confidence %f to %s', (confidence, expected) => {
    const wrapper = mount(ObjectTags, { props: { objects: [makeObject({ confidence })] } });

    expect(badgeTexts(wrapper)).toEqual([`dog ${expected}`]);
  });

  it('does not mutate the objects prop when sorting', () => {
    const objects = [
      makeObject({ id: 'a', confidence: 0.2 }),
      makeObject({ id: 'b', confidence: 0.9 }),
    ];

    mount(ObjectTags, { props: { objects } });

    expect(objects.map((o) => o.id)).toEqual(['a', 'b']);
  });

  it('re-sorts when new objects arrive', async () => {
    const wrapper = mount(ObjectTags, { props: { objects: [] } });

    await wrapper.setProps({
      objects: [
        makeObject({ id: 'a', class_name: 'cup', confidence: 0.3 }),
        makeObject({ id: 'b', class_name: 'dog', confidence: 0.8 }),
      ],
    });

    expect(badgeTexts(wrapper)).toEqual(['dog 80%', 'cup 30%']);
  });
});
