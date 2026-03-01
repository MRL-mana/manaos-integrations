import * as matchers from '@testing-library/jest-dom/matchers'

expect.extend(matchers)

if (!HTMLElement.prototype.scrollTo) {
	HTMLElement.prototype.scrollTo = () => {}
}
