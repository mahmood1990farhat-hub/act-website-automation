import { StylesConfig } from "react-select";

const CustomColors = {
  primary: "#ffd100", 
  black: "#000000",
};

export const selectStyles: StylesConfig<any, boolean> = {
	option: (provided, state) => ({
		...provided,
		backgroundColor: state.isFocused ? CustomColors.primary : undefined,
		color: state.isFocused ? "white" : undefined,
		height: '40px',
		display: "flex",
		alignItems: "center",
		fontSize: '16px', // Prevent mobile zooming
	}),
	menu: (provided) => ({
		...provided,
		backgroundColor: "#FFFFFF",
		position: 'absolute',
		zIndex: 9999,
		fontSize: '16px', // Prevent mobile zooming
	}),
	menuList: (provided) => ({
		...provided,
		padding: 0,
		maxHeight: '150px',
		overflowY: 'auto',
	}),
	control: (base, state) => ({
		...base,
		height: 'auto',
		minHeight: '2.75rem',
		padding: '0.375rem 0.75rem',
		backgroundColor: state.isDisabled ? '#f3f4f6' : 'white',
		boxShadow: 'none',
		borderWidth: '2px',
		borderStyle: 'solid',
		borderColor: state.isFocused ? CustomColors.primary : 'rgb(229 231 235)',
		outlineOffset: '2px',
		'&:hover': {
			borderColor: state.isDisabled ? 'rgb(229 231 235)' : CustomColors.primary,
		},
		transition: 'all 0.2s ease',
		borderRadius: '0.5rem',
		fontSize: '16px', // Prevent mobile zooming
		lineHeight: '1.25rem',
		cursor: state.isDisabled ? 'not-allowed' : 'default',
	}),
	placeholder: (provided, state) => ({
		...provided,
		color: `${CustomColors.black}80`,
		fontSize: '16px', // Prevent mobile zooming
	}),
	input: (provided, state) => ({
		...provided,
		color: 'inherit',
		cursor: (state as any).isDisabled ? 'not-allowed' : 'text',
		fontSize: '16px', // Prevent mobile zooming
		'&:focus': {
			outline: 'none',
			ring: 'none !important',
			boxShadow: 'none !important',
		},
	}),
	singleValue: (provided, state) => ({
		...provided,
		color: (state as any).isDisabled ? `${CustomColors.black}60` : 'inherit',
		fontSize: '16px', // Prevent mobile zooming
	}),
	indicatorSeparator: (provided, state) => ({
		...provided,
		backgroundColor: (state as any).isDisabled ? 'rgb(229 231 235)' : provided.backgroundColor,
	}),
	dropdownIndicator: (provided, state) => ({
		...provided,
		color: (state as any).isDisabled ? 'rgb(156 163 175)' : provided.color,
		cursor: (state as any).isDisabled ? 'not-allowed' : provided.cursor,
	}),
	clearIndicator: (provided, state) => ({
		...provided,
		color: (state as any).isDisabled ? 'rgb(156 163 175)' : provided.color,
		cursor: (state as any).isDisabled ? 'not-allowed' : provided.cursor,
	}),
};